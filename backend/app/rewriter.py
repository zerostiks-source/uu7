"""改写编排：按段落语言路由 + 引擎选择 + 失败重试 + 锁定项校验 + 失败回退。

引擎策略：
- auto：该段落语言有可用模型供应商时走模型改写，否则自动回退本地规则润色；
- llm：强制模型改写，该语言未配置时明确报错；
- local：强制本地规则润色，完全离线可用。

语言路由按段落进行（论文常含中文正文 + 英文摘要/引用），
每段记录实际使用的语言与供应商，便于前端逐段复核。
"""

from __future__ import annotations

import time
from typing import Literal

RewriteStatus = Literal["ok", "reverted", "failed"]
from concurrent.futures import ThreadPoolExecutor

from .config import settings
from .detector import detect_language, score_text
from .local_rewriter import local_rewrite
from .locking import extract_locked_spans, verify_locked_spans
from .provider import LLMError, LLMProvider
from .schemas import RewrittenSegment
from .segmenter import is_title, split_paragraphs

# 判定"是否发生改写"的最低差异：字符相似度过高视为未改动
_CHANGE_THRESHOLD = 0.98
LOCAL_ENGINE_NAME = "local-rules"
# 模型段落并行上限：逐段串行会让长文的等待时间线性增长
_LLM_MAX_WORKERS = 3


def _similarity(a: str, b: str) -> float:
    """简单字符级相似度（基于最长公共子序列比值），用于判断是否真的改写了。"""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # 用集合交集近似，成本低，够用于"是否改动"判定
    set_a, set_b = set(a), set(b)
    inter = len(set_a & set_b)
    union = len(set_a | set_b) or 1
    jaccard = inter / union
    len_ratio = min(len(a), len(b)) / max(len(a), len(b))
    return round(0.5 * jaccard + 0.5 * len_ratio, 4)


def _select_engine(
    engine: str, provider_name: str | None, language: str
) -> tuple[LLMProvider | None, str, str]:
    """按语言选供应商，返回 (模型适配器, 引擎标识, 展示名称)。"""
    cfg = (
        settings.get_provider(provider_name)
        if provider_name
        else settings.get_provider_for_language(language)
    )
    if engine == "llm" and (cfg is None or not cfg.is_ready()):
        raise LLMError(
            f"已选择模型引擎，但语言 {language} 没有可用的模型供应商；"
            "请在 providers.json 配置对应 language 的条目，或改用本地规则引擎"
        )
    if engine == "llm" or (engine == "auto" and cfg is not None and cfg.is_ready()):
        assert cfg is not None
        return LLMProvider(cfg), "llm", cfg.name
    return None, "local", LOCAL_ENGINE_NAME


def rewrite_text(
    text: str,
    strength: str,
    provider_name: str | None = None,
    *,
    engine: str = "auto",
    style: str = "academic",
    glossary: list[str] | None = None,
    only_high_risk: bool = False,
    high_risk_threshold: float = 55.0,
    variant: int = 0,
    language: str = "auto",
) -> tuple[list[RewrittenSegment], str, str]:
    """返回 (分段结果, 供应商展示名, 引擎标识)。language 可强制整篇按指定语言处理。"""
    paragraphs = split_paragraphs(text)
    results: list[RewrittenSegment | None] = [None] * len(paragraphs)
    labels: list[str] = []
    engines: set[str] = set()
    tasks: list[tuple[int, LLMProvider | None, str, list[str], str, str]] = []

    for idx, para in enumerate(paragraphs):
        lang = detect_language(para) if language == "auto" else language
        provider, eng, label = _select_engine(engine, provider_name, lang)
        engines.add(eng)
        if label not in labels:
            labels.append(label)
        locked = extract_locked_spans(para, glossary)

        # 标题段落不改写；精准模式下低风险段落原样保留
        if is_title(para) or (only_high_risk and score_text(para) < high_risk_threshold):
            results[idx] = RewrittenSegment(
                index=idx, original=para, rewritten=para,
                changed=False, locked_spans=locked, status="ok",
                language=lang, provider=label,
            )
            continue
        tasks.append((idx, provider, para, locked, lang, label))

    def _run(
        task: tuple[int, LLMProvider | None, str, list[str], str, str],
    ) -> tuple[int, str, RewriteStatus, str, list[str], str, str]:
        idx, provider, para, locked, lang, label = task
        status: RewriteStatus
        if provider is not None:
            rewritten, status = _rewrite_one(provider, para, strength, locked, style, lang)
        else:
            rewritten = local_rewrite(para, strength, style, locked, variant)
            status = "reverted" if verify_locked_spans(rewritten, locked) else "ok"
            if status == "reverted":
                rewritten = para
        return idx, rewritten, status, para, locked, lang, label

    if tasks:
        workers = min(_LLM_MAX_WORKERS, len(tasks)) if any(t[1] is not None for t in tasks) else 1
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for idx, rewritten, status, para, locked, lang, label in pool.map(_run, tasks):
                results[idx] = RewrittenSegment(
                    index=idx,
                    original=para,
                    rewritten=rewritten,
                    changed=status == "ok" and _similarity(para, rewritten) < _CHANGE_THRESHOLD,
                    locked_spans=locked,
                    status=status,
                    language=lang,
                    provider=label,
                )

    engine_name = "llm" if engines == {"llm"} else ("local" if engines == {"local"} else "mixed")
    return [r for r in results if r is not None], " / ".join(labels) or LOCAL_ENGINE_NAME, engine_name


def rewrite_paragraph(
    text: str,
    strength: str,
    provider_name: str | None = None,
    *,
    engine: str = "auto",
    style: str = "academic",
    glossary: list[str] | None = None,
    variant: int = 1,
    language: str = "auto",
) -> tuple[str, str, list[str]]:
    """单段「换一种写法」，返回 (文本, 引擎标识, 锁定片段)。"""
    lang = detect_language(text) if language == "auto" else language
    provider, engine_name, _ = _select_engine(engine, provider_name, lang)
    locked = extract_locked_spans(text, glossary)
    if provider is not None:
        rewritten, _ = _rewrite_one(provider, text, strength, locked, style, lang)
    else:
        rewritten = local_rewrite(text, strength, style, locked, variant)
        if verify_locked_spans(rewritten, locked):
            rewritten = text
    return rewritten, engine_name, locked


def _rewrite_one(
    provider: LLMProvider,
    para: str,
    strength: str,
    locked: list[str],
    style: str,
    language: str,
) -> tuple[str, RewriteStatus]:
    """改写单段，返回 (文本, 状态)。状态：ok / reverted / failed。"""
    last_error: Exception | None = None
    for attempt in range(settings.max_retry + 1):
        try:
            candidate = provider.rewrite(para, strength, locked, style, language)
        except LLMError as exc:
            last_error = exc
            if attempt < settings.max_retry:
                time.sleep(min(2 ** attempt, 4))
            continue

        missing = verify_locked_spans(candidate, locked)
        if missing:
            # 锁定项被破坏 → 回退原文
            return para, "reverted"
        return candidate, "ok"

    # 重试耗尽 → 标记失败，保留原文
    _ = last_error
    return para, "failed"


def proxy_detect(text: str) -> tuple[float, list[tuple[int, str, float]]]:
    paragraphs = split_paragraphs(text)
    segments = [(i, p, score_text(p)) for i, p in enumerate(paragraphs)]
    overall = score_text(text)
    return overall, segments
