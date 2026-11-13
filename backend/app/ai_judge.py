"""模型辅助的 AI 特征评估。

与 detector.py 的本地启发式规则是两条独立路径：
- 本地规则：可枚举模板匹配，毫秒级，但只覆盖已收录表达，漏检较多；
- 模型评估：由 LLM 逐段给出可疑度与理由，慢且主观，仅作参考。

结论口径：输出风格可疑度与可核对证据，用于定位优先复核的段落，不作为来源判定。
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor

from .config import ProviderConfig
from .detector import analyze_text, detect_language
from .provider import LLMError, LLMProvider
from .segmenter import split_paragraphs

_MAX_WORKERS = 3

# (JSON 键, 展示标签)：两个语言的提示词都使用固定英文键，避免中英混用导致取不到值
_DIMENSIONS = (
    ("stock_phrasing", "套话与连接词"),
    ("mechanical_syntax", "句式机械度"),
    ("information_density", "信息密度"),
    ("missing_voice", "个人风格缺失"),
)

_DIMENSION_SCHEMA = (
    '{"stock_phrasing": 0-100, "mechanical_syntax": 0-100, '
    '"information_density": 0-100, "missing_voice": 0-100}'
)

_SYSTEM_ZH = (
    "你是文本风格分析助手。判断给定中文段落有多大程度上呈现大语言模型生成的典型特征，"
    "并给出可核对的证据。这是主观风格判断，不是概率估计。\n"
    "只输出一个 JSON 对象，不要 Markdown 代码块，不要任何额外文字。结构：\n"
    '{"suspicion": 0-100 的整数, "reasons": ["不超过 4 条中文短句，说明判断依据"], '
    '"evidence": ["原文中最可疑的 1-3 个片段，逐字引用"], '
    '"dimensions": ' + _DIMENSION_SCHEMA + "}\n"
    "若段落本身是标题、公式或参考文献，suspicion 给 0 并在 reasons 里说明原因。"
)

_SYSTEM_EN = (
    "You analyse writing style. Judge how strongly the given English paragraph shows typical "
    "large-language-model traits, and provide checkable evidence. This is a subjective style "
    "judgement, not a probability estimate.\n"
    "Output only one JSON object, no Markdown fences, no extra text. Schema:\n"
    '{"suspicion": integer 0-100, "reasons": ["up to 4 short English sentences"], '
    '"evidence": ["1-3 most suspicious verbatim snippets"], '
    '"dimensions": ' + _DIMENSION_SCHEMA + "}\n"
    "If the paragraph is a heading, formula or reference list, set suspicion to 0 and say why."
)

_CAVEAT = (
    "模型评估由 GLM 逐段给出风格线索：同一文本重跑可能略有波动。"
    "结果用于定位优先复核的段落，请结合逐句证据与人工判断。"
)

_SOURCE_NOTE = (
    "模型风格评估（GLM）：按段落给出程式化表达强弱与依据，用于修订定位"
)

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _clamp(value: object, default: float = 0.0) -> float:
    try:
        num = float(str(value))
    except (TypeError, ValueError):
        return default
    return max(0.0, min(100.0, num))


def _parse(raw: str) -> dict[str, object] | None:
    match = _JSON_RE.search(raw or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _texts(items: object, limit: int) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in out:
            out.append(text[:80])
        if len(out) >= limit:
            break
    return out


def _dimension(payload: dict[str, object], key: str) -> float:
    raw = payload.get("dimensions")
    if not isinstance(raw, dict):
        return 0.0
    for name, value in raw.items():
        if str(name).strip() == key:
            return _clamp(value)
    return 0.0


def analyze_with_model(text: str, config: ProviderConfig) -> dict[str, object]:
    """逐段调用模型评估，返回与本地检测同形的报告字典。"""
    paragraphs = [p for p in split_paragraphs(text) if p.strip()]
    if not paragraphs:
        raise LLMError("模型评估需要有效文本")

    provider = LLMProvider(config)

    def _one(paragraph: str) -> dict[str, object] | None:
        lang = detect_language(paragraph)
        system = _SYSTEM_EN if lang == "en" else _SYSTEM_ZH
        user = ("[TEXT]\n" + paragraph) if lang == "en" else ("【待分析文本】\n" + paragraph)
        try:
            raw = provider.complete(system, user, temperature=0.2)
        except LLMError:
            return None
        return _parse(raw)

    workers = min(_MAX_WORKERS, len(paragraphs)) or 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(_one, paragraphs))

    pairs = [(p, r) for p, r in zip(paragraphs, outcomes) if r is not None]
    if not pairs:
        raise LLMError("模型评估全部失败，请检查模型供应商配置或稍后重试")

    weight_total = sum(len(p) for p, _ in pairs) or 1
    score = round(
        sum(_clamp(r.get("suspicion")) * len(p) for p, r in pairs) / weight_total, 1
    )

    metrics = []
    for key, label in _DIMENSIONS:
        value = sum(_dimension(r, key) * len(p) for p, r in pairs) / weight_total
        metrics.append(
            {
                "key": key,
                "label": label,
                "score": round(value, 1),
                "weight": 25,
                "note": "模型主观打分，四项等权，仅作参考",
            }
        )

    sentences = []
    for index, (paragraph, payload) in enumerate(pairs):
        value = round(_clamp(payload.get("suspicion")), 1)
        sentences.append(
            {
                "index": index,
                "text": paragraph,
                "score": value,
                "level": "high" if value >= 70 else "medium" if value >= 40 else "low",
                "hits": _texts(payload.get("reasons"), 3),
            }
        )

    reasons: list[str] = []
    for _, payload in pairs:
        for reason in _texts(payload.get("reasons"), 4):
            if reason not in reasons:
                reasons.append(reason)

    stats_raw = analyze_text(text).get("stats")
    stats = dict(stats_raw) if isinstance(stats_raw, dict) else {}

    return {
        "score": score,
        "source": "llm",
        "source_note": _SOURCE_NOTE,
        "segments": [
            {"index": i, "text": p, "score": round(_clamp(r.get("suspicion")), 1)}
            for i, (p, r) in enumerate(pairs)
        ],
        "metrics": metrics,
        "sentences": sentences,
        "high_risk_count": sum(1 for item in sentences if item["level"] == "high"),
        "pattern_hits": reasons[:12],
        "caveat": _CAVEAT,
        "stats": stats,
    }
