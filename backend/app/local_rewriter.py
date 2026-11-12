"""本地规则润色引擎：不依赖外部模型即可跑通「检测 → 改写 → 导出」闭环。

只做保义变换，不新增事实、不改动数据/引用/公式：
1. 锁定片段用私有区占位符保护，改写后逐项还原并校验；
2. 模板化连接词/套话替换为更自然的学术表达；
3. 有限同义词表替换，提升用词多样性；
4. 长句拆分、短句合并，打散过于均匀的句长分布；
5. 支持三档强度、三种风格与 variant（用于「换一种写法」）。

定位：离线可用的轻度润色与流程体验；接入模型供应商后可切换为深度语义改写。
"""

from __future__ import annotations

import re

from .locking import verify_locked_spans

_MASK_L = "\ue000"
_MASK_R = "\ue001"

_STYLE_INDEX = {"academic": 0, "concise": 1, "natural": 2}
_STRENGTH_LIMIT = {"light": 1, "medium": 3, "heavy": 6}

# 等义替换：key 为模板化表达，候选为更自然/更多样的写法
_ZH_CONNECTORS: dict[str, tuple[str, ...]] = {
    "综上所述": ("综合上述分析", "把这些讨论收拢来看", "归纳起来"),
    "总而言之": ("整体上看", "概括来说", "归结起来"),
    "值得注意的是": ("这里需要注意的是", "有一个细节需留意", "需要留意的是"),
    "具有重要意义": ("其价值不容忽视", "意义不容低估", "价值较为突出"),
    "在很大程度上": ("大体上", "相当程度上", "多数情况下"),
    "在此基础上": ("沿着这一前提", "据此", "在这一基础上"),
    "不难看出": ("可以看出", "容易发现", "看得出来"),
    "换句话说": ("换一种表述", "说得直白些", "也就是说"),
    "与此同时": ("同一时期", "与之并行的是", "在此期间"),
    "由此可见": ("据此可以推断", "从这一点看", "由此可以看出"),
    "另一方面": ("就另一层面而言", "从另一侧看", "其二"),
    "一方面": ("就一个层面而言", "从一侧看", "其一"),
    "总的来说": ("大体上看", "整体而言", "概括地说"),
    "快速发展": ("迅速演进", "持续推进", "快速演进"),
    "显著提高": ("明显提升", "有明显改善", "提升较为明显"),
    "首先": ("起步时", "先从", "一开始"),
    "其次": ("再者", "紧随其后", "第二点"),
    "此外": ("另有一点", "还有", "除此以外"),
    "另外": ("另有一点", "还有", "另一方面"),
    "进一步": ("更深入地", "再往下", "继续"),
    "因此": ("所以", "由此", "因而"),
    "然而": ("不过", "但", "然而"),
    "并且": ("同时", "且", "并且"),
    "随着": ("伴随", "在", "随着"),
}

_ZH_SYNONYMS: dict[str, tuple[str, ...]] = {
    "方法": ("思路", "做法", "路径"),
    "问题": ("议题", "难点", "问题"),
    "重要": ("关键", "要紧", "核心"),
    "影响": ("作用", "牵动", "影响"),
    "分析": ("梳理", "剖析", "分析"),
    "表明": ("显示", "提示", "反映"),
    "可以": ("能够", "可", "可以"),
    "需要": ("有待", "需", "需要"),
    "进行": ("开展", "做", "进行"),
    "得到": ("获得", "取得", "得到"),
    "存在": ("有", "留存", "存在"),
    "不仅": ("不只", "不单", "不仅"),
}

_ZH_REDUNDANT: dict[str, tuple[str, ...]] = {
    "在一定程度上": ("大体上", "", "大致"),
    "可以说": ("", "", "不妨说"),
    "相对而言": ("相比之下", "", "比较来看"),
}

_EN_CONNECTORS: dict[str, tuple[str, ...]] = {
    "furthermore": ("also", "in addition", "what is more"),
    "moreover": ("also", "besides", "beyond that"),
    "additionally": ("also", "in addition", "on top of that"),
    "consequently": ("as a result", "thus", "so"),
    "in conclusion": ("taken together", "overall", "to sum up"),
    "it is worth noting": ("one detail matters here", "note that", "it helps to note"),
    "it is important to note": ("one point deserves attention", "note that", "it helps to note"),
    "notably": ("in particular", "of note", "especially"),
    "overall": ("taken together", "in general", "by and large"),
    "ultimately": ("in the end", "finally", "at bottom"),
    "in essence": ("at its core", "in short", "basically"),
    "plays a crucial role": ("matters a great deal", "is central", "carries much weight"),
    "a wide range of": ("many", "a broad set of", "numerous"),
    "significantly": ("markedly", "clearly", "considerably"),
}

_EN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "important": ("key", "central", "critical"),
    "significant": ("notable", "marked", "substantial"),
    "utilize": ("use", "employ", "apply"),
    "demonstrate": ("show", "indicate", "reveal"),
    "however": ("yet", "still", "nevertheless"),
    "therefore": ("thus", "hence", "as a result"),
    "method": ("approach", "procedure", "technique"),
    "results": ("findings", "outcomes", "results"),
}

# 英文 AI 高频句式 → 等义、更自然的表达（只替换引导短语，不动句子主干）
_EN_PHRASE_REWRITES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (r"\bWhat is also important here is that\b", ("It also matters that", "Another point is that")),
    (r"\bWhat is important here is that\b", ("The point that matters is that", "A further point is that")),
    (r"\bWhat is important is that\b", ("The key point is that", "What matters is that")),
    (r"\bIt is worth noting that\b", ("One detail worth noting is that", "It helps to note that")),
    (r"\bIt is important to note that\b", ("One point to keep in mind is that", "It helps to note that")),
    (r"\bIn reality,\s*", ("As things stand, ", "In this case, ")),
    (r"\bIn conclusion,\s*", ("Taken together, ", "To wrap up, ")),
    (r"\bThis challenges\b", ("This calls into question", "This complicates")),
    (r"\bThis highlights\b", ("This draws attention to", "This points to")),
    (r"\bThis underscores\b", ("This draws attention to", "This points to")),
    (r"\bwhere we assume\b", ("which rests on the assumption that", "which takes for granted that")),
    (r"\bplays a crucial role\b", ("matters a great deal", "carries much weight")),
)

_NOT_ONLY = re.compile(r"\bnot only\b\s+(.{1,140}?)\s+\bbut also\b\s+", re.IGNORECASE | re.DOTALL)


def _keep_case(raw: str, choice: str) -> str:
    if raw[:1].isupper():
        return choice[:1].upper() + choice[1:]
    return choice[:1].lower() + choice[1:]


def _rewrite_en_templates(text: str, pick: int) -> str:
    """把可枚举的英文 AI 句式换成等义表达，保持句子主干与信息不变。"""
    for pattern, choices in _EN_PHRASE_REWRITES:
        def repl(match: re.Match[str], options: tuple[str, ...] = choices) -> str:
            return _keep_case(match.group(0), options[pick % len(options)])
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    def both(match: re.Match[str]) -> str:
        head = "Both " if match.group(0)[:1].isupper() else "both "
        middle = match.group(1).strip().rstrip(",")
        return head + middle + " and "

    return _NOT_ONLY.sub(both, text, count=1)


def _mask_spans(text: str, spans: list[str]) -> tuple[str, dict[str, str]]:
    """把锁定片段替换为占位符，避免任何规则改动它们。"""
    masked = text
    mapping: dict[str, str] = {}
    for span in sorted({s for s in spans if s}, key=lambda s: (-len(s), s)):
        if span not in masked:
            continue
        token = f"{_MASK_L}{len(mapping)}{_MASK_R}"
        mapping[token] = span
        masked = masked.replace(span, token)
    return masked, mapping


def _replace_table(
    text: str, table: dict[str, tuple[str, ...]], pick: int, limit: int, ignore_case: bool = False
) -> str:
    """按词表做一次性替换；长词优先，替换结果不会被二次扫描。"""
    keys = sorted(table, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(k) for k in keys), re.IGNORECASE if ignore_case else 0)
    counter = [0]

    def repl(match: re.Match[str]) -> str:
        if counter[0] >= limit:
            return match.group(0)
        counter[0] += 1
        raw = match.group(0)
        key = next((k for k in keys if k.lower() == raw.lower()), raw) if ignore_case else raw
        choices = table.get(key)
        if not choices:
            return raw
        choice = choices[pick % len(choices)]
        if ignore_case and raw[:1].isupper():
            return choice[:1].upper() + choice[1:]
        return choice

    return pattern.sub(repl, text)


def _split_zh(para: str) -> list[str]:
    return [s for s in re.split(r"(?<=[。！？；])", para) if s]


def _split_en(para: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", para) if s]


def _split_long(sentence: str) -> str:
    """把中文长句从中间逗号处断为两句，只改标点，不改语义。"""
    parts = sentence.split("，")
    if len(parts) < 3:
        return sentence
    pos = max(1, len(parts) // 2)
    head = "，".join(parts[:pos]).rstrip("。！？；") + "。"
    tail = "，".join(parts[pos:])
    return head + tail


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def _reshape(sents: list[str], lang: str, strength: str, style: str, variant: int) -> list[str]:
    """合并过短句、拆分过长句，打散 AI 文本常见的均匀句长。"""
    if strength == "light" or len(sents) < 2:
        return sents

    out: list[str] = []
    i = 0
    while i < len(sents):
        cur = sents[i]
        if lang == "zh" and strength == "heavy":
            cur = _split_long(cur)

        short_pair = (
            i + 1 < len(sents)
            and len(cur) < 32
            and len(sents[i + 1]) < 42
            and style != "concise"
            and (i + variant) % 2 == 0
        )
        if short_pair:
            nxt = sents[i + 1]
            if lang == "zh":
                out.append(cur.rstrip("。！？；") + "；" + nxt)
            else:
                out.append(cur.rstrip(".!?") + "; " + _lower_first(nxt))
            i += 2
            continue
        out.append(cur)
        i += 1
    return out


def _rewrite_masked(masked: str, strength: str, style: str, variant: int) -> str:
    stripped = re.sub(r"\s", "", masked)
    cjk_ratio = len(re.findall(r"[\u4e00-\u9fa5]", stripped)) / max(len(stripped), 1)
    lang = "zh" if cjk_ratio > 0.12 else "en"

    pick = _STYLE_INDEX.get(style, 0) + variant
    limit = _STRENGTH_LIMIT.get(strength, 3)
    connectors = _ZH_CONNECTORS if lang == "zh" else _EN_CONNECTORS
    synonyms = _ZH_SYNONYMS if lang == "zh" else _EN_SYNONYMS
    ignore_case = lang == "en"

    paragraphs: list[str] = []
    for para in masked.split("\n"):
        if not para.strip():
            paragraphs.append(para)
            continue
        if lang == "en" and strength != "light":
            para = _rewrite_en_templates(para, pick)
        sents = _split_zh(para) if lang == "zh" else _split_en(para)
        rebuilt: list[str] = []
        for sent in sents:
            new = _replace_table(sent, connectors, pick, limit, ignore_case)
            if strength != "light":
                new = _replace_table(new, synonyms, pick, max(1, limit - 1), ignore_case)
            if lang == "zh" and style == "concise":
                new = _replace_table(new, _ZH_REDUNDANT, pick, 2)
            rebuilt.append(new)
        joiner = "" if lang == "zh" else " "
        paragraphs.append(joiner.join(_reshape(rebuilt, lang, strength, style, variant)))
    return "\n".join(paragraphs)


def local_rewrite(
    text: str,
    strength: str = "medium",
    style: str = "academic",
    locked: list[str] | None = None,
    variant: int = 0,
) -> str:
    """返回本地规则润色后的文本；锁定项被破坏时回退原文。"""
    spans = locked or []
    masked, mapping = _mask_spans(text, spans)
    rewritten = _rewrite_masked(masked, strength, style, variant)
    for token, original in mapping.items():
        rewritten = rewritten.replace(token, original)

    if verify_locked_spans(rewritten, spans):
        return text
    if rewritten == text and "，" in text:
        return text.replace("，", "；", 1)
    return rewritten
