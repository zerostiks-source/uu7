"""文本分段：按空行/换行切分段落，保留章节标题层次。

最小闭环版本按段落（以换行为界）切分，过滤空白段；
标题行（以 # 开头或常见的"第X章/一、"等）单独作为一个段落，
以便前端按层次展示。
"""

from __future__ import annotations

import re

_TITLE_PATTERN = re.compile(
    r"^\s*(#{1,6}\s+.+|[一二三四五六七八九十]+[、.．]\s*.+|第[一二三四五六七八九十百零\d]+[章节部分]\s*.*)$"
)


def is_title(line: str) -> bool:
    return bool(_TITLE_PATTERN.match(line.strip()))


def split_paragraphs(text: str) -> list[str]:
    """按空行切分；若无空行则按单换行切分。保留标题为独立段。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) <= 1:
        blocks = [ln.strip() for ln in text.split("\n") if ln.strip()]

    paragraphs: list[str] = []
    for block in blocks:
        if "\n" not in block:
            paragraphs.append(block)
            continue
        # 块内含多行：把标题行与正文行拆开，其余合并为一段
        pending: list[str] = []
        for line in block.split("\n"):
            line = line.strip()
            if not line:
                continue
            if is_title(line):
                if pending:
                    paragraphs.append("\n".join(pending))
                    pending = []
                paragraphs.append(line)
            else:
                pending.append(line)
        if pending:
            paragraphs.append("\n".join(pending))
    return paragraphs
