"""LLM 供应商适配层：统一接口，支持多家 OpenAI 兼容协议的供应商。

业务代码只依赖 `LLMProvider.rewrite()`，不直接依赖任何厂商 SDK。
中文/英文各有一套 system prompt、强度与风格指南；新增供应商只需在
providers.json 增加一条配置（含 language 标记），无需改业务逻辑。
"""

from __future__ import annotations

import httpx

from .config import ProviderConfig

_STRENGTH_GUIDE_ZH = {
    "light": "在保持句式结构基本不变的前提下，仅替换同义词、微调措辞与虚词，改动幅度最小。",
    "medium": "在保持原意的前提下重组句式、调整语序、替换表达方式，可适度合并或拆分句子。",
    "heavy": "在保持原意的前提下对整段进行重写，重新组织论述顺序与句式，改动幅度最大。",
}

_STRENGTH_GUIDE_EN = {
    "light": "Keep the sentence structure intact; adjust only wording and minor phrasing. Minimal change.",
    "medium": "Restructure sentences and reorder clauses while preserving meaning; short sentences may be merged or split.",
    "heavy": "Rewrite the whole paragraph, reorganising the argument order and sentence patterns. Largest change.",
}

_STYLE_GUIDE_ZH = {
    "academic": "保持严谨、正式的学术书面语，避免口语化表达。",
    "concise": "在不丢失信息的前提下压缩冗余修饰，让句式更紧凑。",
    "natural": "让行文更接近人类学者的自然表达，长短句交错，避免机械化排比。",
}

_STYLE_GUIDE_EN = {
    "academic": "Keep a formal, rigorous academic register and avoid colloquial phrasing.",
    "concise": "Remove redundant hedging and modifiers without losing information; keep the prose tight.",
    "natural": "Write like a human scholar: vary sentence length, avoid mechanical parallel lists and stock transitions.",
}

_SYSTEM_PROMPT_ZH = (
    "你是一名学术论文改写助手。你的任务是降低文本的 AI 生成痕迹，使其更接近人类学者的表达习惯，"
    "同时严格保持原文的语义、观点与结论不变。\n"
    "硬性要求：\n"
    "1. 必须以【锁定片段清单】中列出的每一项内容为不可更改的原始片段，在输出中原样逐字保留，"
    "包括方括号、圆括号、数字、百分号、上下标与单位。\n"
    "2. 不得新增事实、数据或结论，不得删除原文观点。\n"
    "3. 只输出改写后的正文，不要输出解释、说明或 Markdown 代码块。\n"
    "4. 输出语言与原文一致。"
)

_SYSTEM_PROMPT_EN = (
    "You are an academic rewriting assistant. Reduce formulaic, machine-like phrasing so the text "
    "reads like a human scholar, while preserving the meaning, claims and conclusions exactly.\n"
    "Hard requirements:\n"
    "1. Every item in [LOCKED SPANS] must appear verbatim in your output, including brackets, "
    "parentheses, numbers, percentages, superscripts, units and formulas.\n"
    "2. Do not add facts, data or conclusions, and do not remove the author's points.\n"
    "3. Output only the rewritten text: no explanations, no Markdown code fences.\n"
    "4. Keep the output in the same language as the source."
)


class LLMError(RuntimeError):
    pass


class LLMProvider:
    """基于 OpenAI 兼容 /chat/completions 协议的通用适配器。"""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    def rewrite(
        self,
        text: str,
        strength: str,
        locked_spans: list[str],
        style: str = "academic",
        language: str = "zh",
    ) -> str:
        if not self.config.is_ready():
            raise LLMError(f"供应商 '{self.config.name}' 配置不完整")

        en = language == "en"
        strength_table = _STRENGTH_GUIDE_EN if en else _STRENGTH_GUIDE_ZH
        style_table = _STYLE_GUIDE_EN if en else _STYLE_GUIDE_ZH
        guide = strength_table.get(strength, strength_table["medium"])
        style_guide = style_table.get(style, style_table["academic"])
        system_prompt = _SYSTEM_PROMPT_EN if en else _SYSTEM_PROMPT_ZH
        locked_block = "\n".join(f"- {s}" for s in locked_spans) or ("(none)" if en else "（无）")

        if en:
            user_prompt = (
                f"[Strength] {strength}: {guide}\n"
                f"[Style] {style}: {style_guide}\n\n"
                f"[LOCKED SPANS]\n{locked_block}\n\n"
                f"[SOURCE TEXT]\n{text}\n\n"
                "Output only the rewritten text."
            )
        else:
            user_prompt = (
                f"【改写强度】{strength}：{guide}\n"
                f"【表达风格】{style}：{style_guide}\n\n"
                f"【锁定片段清单】\n{locked_block}\n\n"
                f"【待改写正文】\n{text}\n\n"
                "请直接输出改写后的正文。"
            )

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMError(f"调用供应商 '{self.config.name}' 失败：{exc}") from exc

        if resp.status_code != 200:
            raise LLMError(
                f"供应商 '{self.config.name}' 返回 {resp.status_code}：{resp.text[:200]}"
            )

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"供应商 '{self.config.name}' 响应格式异常") from exc

        return _strip_code_fence(content.strip())


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text
