"""开源分类器接入：在「规则信号」之外单独提供「模型疑似度」。

设计约束：
- 懒加载 + 后台预热 + 失败降级：加载失败或没装依赖时返回 available=False，
  绝不影响 /api/detect 的规则信号与页面渲染。
- 分段推理：按段落切块送模型，块分数聚合回段落，索引与规则信号的段落对齐。
- 只作写作自检参考，用于定位优先复核的段落，不作为来源判定或机构检测结论。

环境变量：
- AI_DETECT_MODEL=off            关闭分类器
- AI_DETECT_MODEL=<repo|本地目录> 指定模型（覆盖默认值）
- AI_DETECT_HF_ENDPOINT=direct   不自动使用镜像，直连 huggingface.co
- AI_DETECT_HF_MIRROR            镜像地址，默认 https://hf-mirror.com
- AI_DETECT_MAX_CHARS=360        单块最大字符数
- AI_DETECT_OFFLINE=1            只用本地缓存，不联网
- AI_DETECT_WARMUP=0             关闭启动预热
"""

from __future__ import annotations

import os
import re
import threading
import time
from functools import lru_cache
from typing import Any

from .segmenter import split_paragraphs

_OFF_VALUES = {"0", "off", "false", "no"}
_DISABLED = os.getenv("AI_DETECT_MODEL", "").strip().lower() in _OFF_VALUES
_OFFLINE = os.getenv("AI_DETECT_OFFLINE", "").strip().lower() in {"1", "true", "yes", "on"}
_MAX_CHARS = max(120, int(os.getenv("AI_DETECT_MAX_CHARS", "360") or 360))
_MIN_CHARS = 80
_MAX_CHUNKS = 32
_MAX_SENTENCES = int(os.getenv("AI_DETECT_MAX_SENTENCES", "60") or 60)
_COOLDOWN = float(os.getenv("AI_DETECT_RETRY_COOLDOWN", "120"))

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_XIAOYU_LOCAL = os.path.join(_BACKEND_DIR, "models", "xiaoyu-v3.3")

# 默认只使用本地的 2026 中文判别器；.env 丢失时也不会回退到已下线的 2023 模型。
_DEFAULT_MODELS: dict[str, tuple[str, ...]] = {
    "zh": (_XIAOYU_LOCAL,),
    "en": (_XIAOYU_LOCAL,),
}

NOTE_CAVEAT = (
    "该读数来自开源中文判别器，反映文本统计特征与机器生成语料的接近程度；"
    "训练语料不同，换模型读数会变。用于定位优先复核的段落，"
    "不作为来源判定或机构检测结论。"
)
NOTE_LOADING = (
    "模型首次加载中（本地权重，通常 1–2 秒），完成后点「重新自检」即可看到结果"
)

_SENT = re.compile(r"[^。！？!?\n]+[。！？!?]*")

_lock = threading.Lock()
_loaded: dict[str, tuple[Any, Any]] = {}
_errors: dict[str, tuple[float, str]] = {}
_loading: set[str] = set()
_warmed = False


def _prepare_env() -> None:
    """在 import transformers 之前确定端点：默认走镜像，可显式直连。"""
    if os.getenv("HF_ENDPOINT"):
        return
    if os.getenv("AI_DETECT_HF_ENDPOINT", "").strip().lower() == "direct":
        return
    mirror = os.getenv("AI_DETECT_HF_MIRROR", "https://hf-mirror.com").strip()
    if mirror:
        os.environ["HF_ENDPOINT"] = mirror
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "10")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "30")


def _resolve_local(name: str) -> str:
    """本地目录支持相对 backend/ 的写法（如 models/xiaoyu-v3.3）。"""
    if os.path.isdir(name):
        return os.path.abspath(name)
    candidate = os.path.join(_BACKEND_DIR, name)
    if os.path.isdir(candidate):
        return candidate
    return name


def _candidates(lang: str) -> tuple[str, ...]:
    override = os.getenv("AI_DETECT_MODEL", "").strip()
    if override and override.lower() not in _OFF_VALUES:
        return (_resolve_local(override),)
    return _DEFAULT_MODELS.get(lang, _DEFAULT_MODELS["zh"])


def _unavailable(model: str, note: str) -> dict[str, Any]:
    return {
        "available": False,
        "model": model,
        "label": "unavailable",
        "probability": 0.0,
        "note": note,
        "segments": [],
        "sentences": [],
        "segment_count": 0,
        "high_ratio": 0.0,
        "band": "unavailable",
        "evidence_level": "unavailable",
        "evidence": [],
    }


def _assess_evidence(
    text: str, segments: list[dict[str, Any]], sentences: list[dict[str, Any]]
) -> tuple[str, list[str]]:
    """证据充分度：看样本量与段落判定一致性，不是统计校准，也不代表准确率。"""
    n = len(segments)
    scores = [float(s["score"]) for s in segments]
    high = sum(1 for x in scores if x >= 50)
    evidence = [
        f"{n} 段中 {high} 段（{round(high / max(n, 1) * 100)}%）被判为疑似 AI（≥50 分）"
    ]
    if sentences:
        marked = sum(1 for s in sentences if float(s["score"]) >= 50)
        evidence.append(f"{marked} 句被标记为优先复核")
    if n < 2 or len(text.strip()) < 150:
        return "limited", evidence + ["段落或文本过短，证据不足以形成稳定判断"]
    mean = sum(scores) / n
    std = (sum((x - mean) ** 2 for x in scores) / n) ** 0.5
    evidence.append(f"段落读数离散度 {std:.1f} / 100")
    if std <= 18 and n >= 4:
        return "sufficient", evidence + ["各段落判定方向一致"]
    if std <= 35:
        return "partial", evidence + ["部分段落判定存在分歧，建议逐段看"]
    return "limited", evidence + ["段落间判定分歧较大，建议逐段人工复核"]


def _load_one(name: str) -> tuple[Any, Any]:
    is_local_dir = os.path.isdir(name)
    if not is_local_dir:
        _prepare_env()
    try:
        import torch  # noqa: F401
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except Exception:  # pragma: no cover - 依赖缺失分支
        raise RuntimeError(
            "未安装 torch / transformers，模型疑似度不可用；"
            "安装：pip install -r backend/requirements-detector.txt"
        ) from None
    tokenizer = AutoTokenizer.from_pretrained(name, local_files_only=_OFFLINE)
    model = AutoModelForSequenceClassification.from_pretrained(name, local_files_only=_OFFLINE)
    model.eval()
    return tokenizer, model


def _engine(lang: str) -> tuple[str, tuple[Any, Any]]:
    """返回 (模型名, (tokenizer, model))；加载失败时抛出可读异常。"""
    for name in _candidates(lang):
        with _lock:
            if name in _loaded:
                return name, _loaded[name]
            failed = _errors.get(name)
            if failed is not None and time.time() - failed[0] < _COOLDOWN:
                continue
            try:
                pair = _load_one(name)
            except Exception as exc:
                _errors[name] = (time.time(), f"{type(exc).__name__}: {exc}")
                continue
            _loaded[name] = pair
            _errors.pop(name, None)
            return name, pair
    first = _candidates(lang)[0]
    failed = _errors.get(first)
    raise RuntimeError(failed[1] if failed else "没有可用的检测模型")


def _ensure_loading(lang: str) -> bool:
    """后台加载模型，立即返回是否已经/正在加载。"""
    if _DISABLED or _OFFLINE:
        return False
    with _lock:
        if any(name in _loaded for name in _candidates(lang)):
            return True
        pending = [name for name in _candidates(lang)
                   if name not in _loading
                   and time.time() - _errors.get(name, (0.0, ""))[0] >= _COOLDOWN]
        if not pending:
            return bool(_loading)
        _loading.update(pending)

    def worker() -> None:
        try:
            _engine(lang)
        except Exception:
            pass
        finally:
            with _lock:
                _loading.difference_update(pending)

    threading.Thread(target=worker, daemon=True, name="classifier-load").start()
    return True


def warmup() -> None:
    """应用启动时预热，避免首次检测请求被下载阻塞。"""
    global _warmed
    if _warmed or _DISABLED:
        return
    if os.getenv("AI_DETECT_WARMUP", "1").strip().lower() in _OFF_VALUES:
        return
    _warmed = True
    _ensure_loading("zh")


def _ai_index(model: Any) -> int:
    """在 id2label 里定位「AI / 机器生成」对应的类别下标。"""
    labels = getattr(getattr(model, "config", None), "id2label", None) or {}
    for key, value in labels.items():
        text = str(value).lower()
        if "human" in text or "real" in text or "genuine" in text:
            continue
        if any(k in text for k in ("chatgpt", "fake", "machine", "ai", "generated")):
            return int(key)
    if len(labels) >= 2:
        return 1
    return 0


def _split_long(paragraph: str) -> list[str]:
    if len(paragraph) <= _MAX_CHARS:
        return [paragraph]
    pieces: list[str] = []
    buf = ""
    for sentence in _SENT.findall(paragraph):
        if len(buf) + len(sentence) <= _MAX_CHARS:
            buf += sentence
            continue
        if buf:
            pieces.append(buf)
        buf = sentence
        while len(buf) > _MAX_CHARS:
            pieces.append(buf[:_MAX_CHARS])
            buf = buf[_MAX_CHARS:]
    if buf:
        pieces.append(buf)
    return pieces


def _chunks(text: str) -> list[tuple[int, str]]:
    items: list[tuple[int, str]] = []
    for index, paragraph in enumerate(split_paragraphs(text)):
        for piece in _split_long(paragraph):
            if piece.strip():
                items.append((index, piece))
    return items[:_MAX_CHUNKS]


def _predict_probs(tokenizer: Any, model: Any, pieces: list[str]) -> tuple[float, ...]:
    """兼容两类分类头：单 logit + sigmoid 与双 logit + softmax。"""
    import torch

    with torch.no_grad():
        batch = tokenizer(
            pieces,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        logits = model(**batch).logits
    num_labels = getattr(getattr(model, "config", None), "num_labels", 2)
    if num_labels == 1:
        return tuple(float(p) for p in torch.sigmoid(logits).reshape(-1).tolist())
    ai_index = _ai_index(model)
    return tuple(float(p) for p in torch.softmax(logits, dim=-1)[:, ai_index].tolist())


@lru_cache(maxsize=24)
def _run(text: str, lang: str) -> tuple[str, tuple[int, ...], tuple[float, ...]]:
    name, pair = _engine(lang)
    tokenizer, model = pair
    items = _chunks(text)
    if not items:
        return name, (), ()
    probs = _predict_probs(tokenizer, model, [piece for _, piece in items])
    return name, tuple(i for i, _ in items), probs


@lru_cache(maxsize=24)
def _sentence_run(text: str, lang: str) -> tuple[tuple[str, float], ...]:
    """逐句推理，供前端定位最可疑的句子。"""
    _, pair = _engine(lang)
    tokenizer, model = pair
    _SENT_CUT = re.compile(r"[^。！？!?\n]+[。！？!?]*")
    sentences = [
        s.strip() for s in _SENT_CUT.findall(text)
        if len(s.strip()) >= 12 and not s.strip().startswith("#")
    ][:_MAX_SENTENCES]
    if not sentences:
        return ()
    probs = _predict_probs(tokenizer, model, sentences)
    return tuple((s, p) for s, p in zip(sentences, probs))


def judge(text: str, lang: str = "zh") -> dict[str, Any]:
    """返回模型疑似度；任何异常都降级为 available=False，不抛给调用方。"""
    model = _candidates(lang)[0]
    if _DISABLED:
        return _unavailable(model, "模型疑似度已关闭（AI_DETECT_MODEL=off）")
    if _OFFLINE and not any(name in _loaded for name in _candidates(lang)):
        return _unavailable(
            model,
            "AI_DETECT_OFFLINE=1 且本地无缓存模型；请先下载权重，再用 AI_DETECT_MODEL 指向本地目录",
        )
    if len(text.strip()) < _MIN_CHARS:
        return _unavailable(model, f"文本不足 {_MIN_CHARS} 字，分类器判定不可靠，已跳过")
    if not any(name in _loaded for name in _candidates(lang)):
        if os.path.isdir(model):
            # 本地目录加载通常 1–2 秒，直接同步，避免首次检测拿不到分数
            try:
                _engine(lang)
            except Exception as exc:
                return _unavailable(model, f"模型加载失败：{exc}")
        else:
            loading = _ensure_loading(lang)
            if loading:
                return _unavailable(model, NOTE_LOADING)
            return _unavailable(model, f"模型加载失败：{_last_error(lang)}")
    try:
        name, indexes, probs = _run(text, lang)
    except Exception as exc:
        return _unavailable(model, str(exc))
    if not probs:
        return _unavailable(name, "未能切分出可推理的段落")

    buckets: dict[int, list[float]] = {}
    for paragraph_index, prob in zip(indexes, probs):
        buckets.setdefault(paragraph_index, []).append(prob)
    segments = [
        {"index": i, "score": round(sum(buckets[i]) / len(buckets[i]) * 100, 1)}
        for i in sorted(buckets)
    ]
    # 整篇分 = 全部推理块的等权均值；段落分布单独用 high_ratio 呈现，避免一个均值掩盖差异
    overall = round(sum(probs) / len(probs) * 100, 1)
    sentences: list[dict[str, Any]] = []
    if os.getenv("AI_DETECT_SENTENCES", "1").strip().lower() not in _OFF_VALUES:
        try:
            pairs = _sentence_run(text, lang)
            sentence_items: list[dict[str, Any]] = [
                {"text": s, "score": round(p * 100, 1)} for s, p in pairs
            ]
            sentences = sorted(sentence_items, key=lambda item: -float(item["score"]))[:12]
        except Exception:
            sentences = []
    evidence_level, evidence = _assess_evidence(text, segments, sentences)
    return {
        "available": True,
        "model": name,
        "label": "ai" if overall >= 50 else "human",
        "probability": overall,
        "note": NOTE_CAVEAT,
        "segments": segments,
        "sentences": sentences,
        "segment_count": len(segments),
        "high_ratio": round(
            sum(1 for s in segments if s["score"] >= 50) / max(len(segments), 1) * 100, 1
        ),
        "band": "high" if overall >= 70 else "medium" if overall >= 40 else "low",
        "evidence_level": evidence_level,
        "evidence": evidence,
    }


def _last_error(lang: str) -> str:
    for name in _candidates(lang):
        failed = _errors.get(name)
        if failed:
            return failed[1]
    return "未知原因，请查看服务端日志"


def status() -> dict[str, Any]:
    names = list(dict.fromkeys(_candidates("zh") + _candidates("en")))
    return {
        "enabled": not _DISABLED,
        "model": names[0],
        "loaded": [n for n in names if n in _loaded],
        "loading": sorted(_loading),
        "errors": {n: v[1] for n, v in _errors.items()},
    }
