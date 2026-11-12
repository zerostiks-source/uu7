"""锁定项识别与校验：保护专业术语、引用文献、数据与公式。

识别策略：
- 引用标注：形如 [1]、[1,2]、[12-15]、(Author, 2020)、(张三，2020)
- 数值/数据：带单位或百分号的数字、纯数字统计、区间
- 公式：行内 $...$、块级 $$...$$、含 = 的表达式片段
- 专业术语：大小写敏感的英文缩写/专有名词（连续大写、驼峰）、
  以及由调用方传入的术语表（术语表为空时仅按规则识别）

锁定项用于：改写 prompt 中要求逐字保留；改写后校验其是否仍然存在。
"""

from __future__ import annotations

import re

_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\[\d+(?:\s*[-,，]\s*\d+)*\]"),                 # [1] [1,2] [12-15]
    re.compile(r"[(（][A-Za-z\u4e00-\u9fa5][^()（）]{0,30}\d{4}[)）]"),  # (Author, 2020)
    re.compile(r"\$\$[^$]+\$\$|\$[^$]+\$"),                       # 行内/块级公式
    re.compile(r"\d+(?:\.\d+)?\s*%"),                             # 百分比
    re.compile(r"\d+(?:\.\d+)?\s*(?:万人|亿元|亿元|万|亿|千米|公斤|米|秒|分钟|小时|天|年|月|日|个|次|项|倍)"),
    re.compile(r"\b[A-Z]{2,}(?:[-/][A-Z0-9]+)*\b"),               # 英文缩写 ACME/GPT-4
    re.compile(r"\b[A-Za-z]+(?:[A-Z][a-z]+)+\b"),                 # 驼峰专有名词
]


def extract_locked_spans(text: str, glossary: list[str] | None = None) -> list[str]:
    """返回文本中的锁定片段（去重、保持出现顺序）。"""
    found: list[str] = []
    seen: set[str] = set()

    def add(span: str) -> None:
        span = span.strip()
        if span and span not in seen:
            seen.add(span)
            found.append(span)

    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            add(match.group(0))

    for term in glossary or []:
        if term and term in text:
            add(term)

    return found


def verify_locked_spans(rewritten: str, spans: list[str]) -> list[str]:
    """返回改写后丢失的锁定项列表（空列表表示全部保留）。"""
    return [s for s in spans if s not in rewritten]
