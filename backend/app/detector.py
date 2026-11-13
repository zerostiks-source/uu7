"""行文特征指数检测（启发式，可复现、可追溯）。

定位：量化可见的行文特征，帮助定位需要人工修订的段落；输出的是内部特征指数，
不是分类器概率，也不替代任何机构检测结论。

特征来源：
- 突发性 Burstiness：句长变异系数（程式化文本常趋于均匀）
- 词汇丰富度 TTR：用词重复程度（短文本会失真，仅作弱信号）
- 套话密度：中英文高频连接词 / 套语词典
- 句式模板：中英文高频句式模式库（正则，可给出可读证据）

输出 0-100 的内部特征指数，并附带命中的具体证据。未命中表示行文未落入当前模板集合。
"""

from __future__ import annotations

import math
import re
from typing import Literal, TypedDict

_SENT_SPLIT = re.compile(r"[。！？!?；;\n]+|(?<=[a-z0-9])\.\s+|(?<=[a-z0-9])\.$")
_CJK = re.compile(r"[\u4e00-\u9fa5]")
_WORD = re.compile(r"[\u4e00-\u9fa5]{1,4}|[A-Za-z]+")

# 中文套话词典
_CANNED_ZH = (
    "首先", "其次", "再次", "此外", "另外", "综上所述", "总而言之",
    "值得注意的是", "总的来说", "不难看出", "由此可见", "换句话说",
    "在当今", "随着", "的发展", "具有重要意义", "有效地", "进一步",
    "一方面", "另一方面", "在此基础上", "与此同时",
)

# 英文套话词典（连接词、套话短语、AI 高频词）
_CANNED_EN = (
    "furthermore", "moreover", "additionally", "consequently", "notably",
    "in conclusion", "overall", "it is worth noting", "it is important to note",
    "in today's", "plays a crucial role", "a testament to", "not only",
    "delve", "tapestry", "crucial", "pivotal", "underscore", "leverage",
    "landscape", "realm", "foster", "navigate", "intricate", "comprehensive",
    "robust", "significantly", "ultimately", "in essence", "that being said",
    "when it comes to", "a wide range of", "it is essential", "serves as",
)

# 句式模板库：比关键词更接近 AI 文本的可枚举结构特征，命中后作为证据展示
_AI_PATTERNS_EN: tuple[tuple[str, str], ...] = (
    (r"\bwhat is (?:also )?(?:important|notable|interesting|worth noting)(?: here)? is that\b", "What is ... is that 强调句式"),
    (r"\bit (?:is|should be) (?:worth noting|important to note|worth mentioning) that\b", "It is worth noting that"),
    (r"\bnot only\b[\s\S]{0,140}?\bbut also\b", "not only ... but also 对称句式"),
    (r"\bthis (?:highlights|suggests|underscores|demonstrates|illustrates|challenges|reflects|indicates|shows)\b", "This + 认知动词 概括句"),
    (r"\bwhere we (?:assume|see|can|often)\b|\bas we (?:assume|know|can see)\b", "where we assume 元评论句式"),
    (r"\bin (?:reality|practice|essence|conclusion|summary|other words)\b", "段首概括连接词"),
    (r"\bit is (?:clear|evident|important|essential|worth) that\b", "It is clear that 断言句式"),
    (r"\b(?:overall|furthermore|moreover|additionally|consequently|ultimately),", "段首正式连接词"),
    (r"\bplays? a (?:crucial|pivotal|vital|key|significant) role\b", "plays a crucial role"),
    (r"\b(?:a wide range of|a variety of|the importance of|serves as)\b", "AI 高频搭配"),
    (r"\bnot only\b|\bin today's\b", "AI 高频起手式"),
)

_AI_PATTERNS_ZH: tuple[tuple[str, str], ...] = (
    (r"随着.{0,24}(?:发展|推进|普及|应用)", "随着…的发展"),
    (r"值得注意的是|不难看出|综上所述|总而言之|由此可见", "套话连接词"),
    (r"在.{0,20}背景下", "在…背景下"),
    (r"具有重要意义|发挥着.{0,8}作用|扮演着.{0,8}角色", "套话谓语"),
    (r"首先[\s\S]{0,160}?其次|一方面[\s\S]{0,160}?另一方面", "机械并列结构"),
    (r"不仅[\s\S]{0,80}?而且|既[\s\S]{0,80}?又", "对称句式"),
)

CAVEAT = (
    "行文特征指数覆盖可枚举的模板化表达；未命中表示行文未落入当前模板集合。"
    "指数用于修订定位，不作为来源判定或机构检测结论，请结合人工复核判断。"
)


class MetricItem(TypedDict):
    """单项信号拆解。"""

    key: str
    label: str
    score: float
    weight: int
    note: str


class SentenceItem(TypedDict):
    """逐句信号定位。"""

    index: int
    text: str
    score: float
    level: Literal["high", "medium", "low"]
    hits: list[str]


class StatsItem(TypedDict):
    """文本统计。"""

    chars: int
    words: int
    paragraphs: int
    sentences: int
    avg_sentence_len: float


class DetectReport(TypedDict):
    """自检报告结构，供 API 层直接映射到 DetectResponse。"""

    score: float
    language: str
    metrics: list[MetricItem]
    sentences: list[SentenceItem]
    high_risk_count: int
    pattern_hits: list[str]
    caveat: str
    stats: StatsItem


def _detect_language(text: str) -> str:
    """按中文字符占比判断语言：占比 > 12% 视为中文，否则英文。"""
    stripped = re.sub(r"\s", "", text)
    if not stripped:
        return "zh"
    cjk_ratio = len(_CJK.findall(stripped)) / len(stripped)
    return "zh" if cjk_ratio > 0.12 else "en"


def detect_language(text: str) -> str:
    """对外暴露语言识别（zh / en），供改写引擎按段落路由。"""
    return _detect_language(text)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _pattern_table(lang: str) -> tuple[tuple[tuple[str, str], ...], int]:
    if lang == "en":
        return _AI_PATTERNS_EN, re.IGNORECASE
    return _AI_PATTERNS_ZH, 0


def _pattern_hits(text: str, lang: str) -> list[str]:
    """返回命中的句式模板标签（去重，保持模板顺序）。"""
    table, flags = _pattern_table(lang)
    return [label for pattern, label in table if re.search(pattern, text, flags)]


def _pattern_count(text: str, lang: str) -> int:
    """返回句式模板命中总次数，用于密度估算。"""
    table, flags = _pattern_table(lang)
    return sum(len(re.findall(pattern, text, flags)) for pattern, _ in table)


def _canned_density(text: str, lang: str) -> float:
    """每 100 字（或 100 词）命中套话的次数。"""
    if lang == "zh":
        hits = sum(text.count(k) for k in _CANNED_ZH)
        base = max(len(text) / 100.0, 1.0)
    else:
        lower = text.lower()
        hits = sum(lower.count(k) for k in _CANNED_EN)
        word_count = len(re.findall(r"[A-Za-z]+", text))
        base = max(word_count / 100.0, 1.0)
    return hits / base


def _signals(text: str, lang: str, sents: list[str]) -> dict[str, float]:
    """计算四项启发式信号（0-100，越高表示模板化信号越强）。"""
    lengths = [len(s) for s in sents]
    mean_len = sum(lengths) / len(lengths) if lengths else 0.0
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths) if lengths else 0.0
    cv = (math.sqrt(variance) / mean_len) if mean_len else 0.0
    # 句长均匀度：以正常行文的 cv≈0.40 为零点，只有明显均匀（长短句失衡）才抬分
    burstiness = _clamp(max(0.0, (0.40 - cv) / 0.40) * 100)

    words = _WORD.findall(text)
    ttr = len(set(words)) / len(words) if words else 1.0
    # 用词重复：以正常行文 TTR≈0.55 为零点（中文按 1-4 字切分 TTR 天然偏高），低于基线才计分
    diversity = _clamp(max(0.0, (0.55 - ttr) / 0.55) * 100)

    # 套话密度：分母 5.0，普通连接词偶发命中不显著抬分
    canned = _clamp(min(_canned_density(text, lang), 5.0) / 5.0 * 100)
    # 句式模板按「每 100 字」归一；零命中得 0 分（不做先验平滑，避免结构性地板）。
    # 密度映射以 0.5 次/100 字为零点，偶发单次命中不抬分；
    # 种类覆盖率要求命中 ≥2 类不同模板才抬分，避免单一偶发命中直接托底。
    base = max(len(text) / 100.0, 1.0)
    density = _pattern_count(text, lang) / base
    table, _ = _pattern_table(lang)
    kind_hits = _pattern_hits(text, lang)
    kinds_cov = max(0.0, (len(kind_hits) - 1) / max(len(table) - 1, 1))
    patterns = _clamp(max(max(0.0, (density - 0.5) / 0.5), kinds_cov) * 100)

    return {
        "burstiness": burstiness,
        "diversity": diversity,
        "canned": canned,
        "patterns": patterns,
    }


def score_text(text: str) -> float:
    """返回 0-100 的行文特征指数（启发式，用于修订定位）。"""
    text = text.strip()
    if not text:
        return 0.0
    lang = _detect_language(text)
    sents = _sentences(text)
    if not sents:
        return 0.0
    s = _signals(text, lang, sents)
    score = (
        0.30 * s["burstiness"]
        + 0.15 * s["diversity"]
        + 0.20 * s["canned"]
        + 0.35 * s["patterns"]
    )
    return round(_clamp(score), 1)


def score_segments(texts: list[str]) -> list[float]:
    return [score_text(t) for t in texts]


def _canned_hits(text: str, lang: str) -> list[str]:
    """返回文本命中的套话条目（去重，保持词典顺序）。"""
    source = text if lang == "zh" else text.lower()
    dictionary = _CANNED_ZH if lang == "zh" else _CANNED_EN
    return [word for word in dictionary if word in source]


def _metrics(text: str, lang: str) -> list[MetricItem]:
    """拆解四项信号，供前端展示「哪类特征被命中」。"""
    sents = _sentences(text)
    s = _signals(text, lang, sents)
    return [
        {
            "key": "burstiness",
            "label": "句式过于均匀",
            "score": round(s["burstiness"], 1),
            "weight": 30,
            "note": "句长接近、缺少长短变化时信号偏强",
        },
        {
            "key": "diversity",
            "label": "用词重复",
            "score": round(s["diversity"], 1),
            "weight": 15,
            "note": "仅作弱信号；短文本 TTR 天然偏高，会低估信号",
        },
        {
            "key": "canned",
            "label": "模板化套话",
            "score": round(s["canned"], 1),
            "weight": 20,
            "note": "高频连接词与套语越多信号越强",
        },
        {
            "key": "patterns",
            "label": "AI 高频句式",
            "score": round(s["patterns"], 1),
            "weight": 35,
            "note": "命中可枚举的句式模板，证据见下方列表",
        },
    ]


def _sentence_risk(sentence: str, lang: str, mean_len: float) -> tuple[float, list[str]]:
    """逐句信号分：套话 + 句式模板 + 句长均匀度 - 真实信息量。"""
    score = 6.0
    hits = _canned_hits(sentence, lang)
    score += min(len(hits) * 12, 36)

    patterns = _pattern_hits(sentence, lang)
    score += min(len(patterns) * 24, 48)
    hits.extend(p for p in patterns if p not in hits)

    length = len(sentence)
    if mean_len and 0.8 <= length / mean_len <= 1.2:
        score += 10
    if lang == "zh" and length > 70 and sentence.count("，") >= 2:
        score += 8

    # 只有真实的数据/引用证据才减分；英文缩写（OT、AI 等）不再当作人工写作证据
    if re.search(r"(?:19|20)\d{2}|\d+(?:\.\d+)?\s*%|\[\d+\]|\d+(?:\.\d+)?\s*(?:kg|cm|mm|ml|mg|km|ms)\b", sentence):
        score -= 8

    return round(_clamp(score), 1), hits


def analyze_text(text: str, threshold: float = 55.0) -> DetectReport:
    """生成自检报告：信号强度、指标分解、命中证据、逐句定位与统计。"""
    clean = text.strip()
    if not clean:
        return {
            "score": 0.0,
            "language": "zh",
            "metrics": [],
            "sentences": [],
            "high_risk_count": 0,
            "pattern_hits": [],
            "caveat": CAVEAT,
            "stats": {"chars": 0, "words": 0, "paragraphs": 0, "sentences": 0, "avg_sentence_len": 0.0},
        }

    lang = _detect_language(clean)
    sents = _sentences(clean)
    mean_len = sum(len(s) for s in sents) / len(sents) if sents else 0.0
    items: list[SentenceItem] = []
    for i, sent in enumerate(sents):
        risk, hits = _sentence_risk(sent, lang, mean_len)
        level: Literal["high", "medium", "low"] = (
            "high" if risk >= threshold else ("medium" if risk >= 30 else "low")
        )
        items.append(
            {"index": i, "text": sent, "score": risk, "level": level, "hits": hits}
        )

    paragraphs = [p for p in re.split(r"\n\s*\n", clean) if p.strip()]
    stats: StatsItem = {
        "chars": len(re.sub(r"\s", "", clean)),
        "words": len(re.findall(r"[A-Za-z]+", clean)) if lang == "en" else len(re.sub(r"\s", "", clean)),
        "paragraphs": max(len(paragraphs), 1),
        "sentences": len(sents),
        "avg_sentence_len": round(mean_len, 1),
    }
    return {
        "score": score_text(clean),
        "language": lang,
        "metrics": _metrics(clean, lang),
        "sentences": items,
        "high_risk_count": sum(1 for item in items if item["level"] == "high"),
        "pattern_hits": _pattern_hits(clean, lang),
        "caveat": CAVEAT,
        "stats": stats,
    }
