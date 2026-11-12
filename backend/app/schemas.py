"""请求/响应数据模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Strength = Literal["light", "medium", "heavy"]
Engine = Literal["auto", "llm", "local"]
Style = Literal["academic", "concise", "natural"]
Language = Literal["auto", "zh", "en"]


class Segment(BaseModel):
    index: int
    text: str
    locked: bool = False


class DetectRequest(BaseModel):
    text: str = Field(..., description="待检测的论文文本")


class SegmentScore(BaseModel):
    index: int
    text: str
    score: float


class Metric(BaseModel):
    key: str
    label: str
    score: float
    weight: int
    note: str


class SentenceRisk(BaseModel):
    index: int
    text: str
    score: float
    level: Literal["high", "medium", "low"]
    hits: list[str] = Field(default_factory=list)


class TextStats(BaseModel):
    chars: int = 0
    words: int = 0
    paragraphs: int = 0
    sentences: int = 0
    avg_sentence_len: float = 0.0


class DetectResponse(BaseModel):
    score: float
    source: Literal["proxy", "official"]
    source_note: str
    segments: list[SegmentScore]
    language: str = "zh"
    metrics: list[Metric] = Field(default_factory=list)
    sentences: list[SentenceRisk] = Field(default_factory=list)
    high_risk_count: int = 0
    pattern_hits: list[str] = Field(default_factory=list)
    caveat: str = ""
    stats: TextStats = Field(default_factory=TextStats)


class RewriteRequest(BaseModel):
    text: str
    strength: Strength = "medium"
    provider: str | None = None
    engine: Engine = "auto"
    style: Style = "academic"
    language: Language = "auto"
    glossary: list[str] = Field(default_factory=list)
    only_high_risk: bool = False
    high_risk_threshold: float = 55.0
    variant: int = 0


class RewriteSegmentRequest(BaseModel):
    text: str
    strength: Strength = "medium"
    provider: str | None = None
    engine: Engine = "auto"
    style: Style = "academic"
    language: Language = "auto"
    glossary: list[str] = Field(default_factory=list)
    variant: int = 1


class RewriteSegmentResponse(BaseModel):
    text: str
    engine: str
    language: str = "zh"
    locked_spans: list[str] = Field(default_factory=list)


class RewrittenSegment(BaseModel):
    index: int
    original: str
    rewritten: str
    changed: bool
    locked_spans: list[str] = Field(default_factory=list)
    status: Literal["ok", "reverted", "failed"]
    language: str = "zh"
    provider: str = ""


class RewriteResponse(BaseModel):
    strength: Strength
    provider: str
    segments: list[RewrittenSegment]
    failed_count: int
    reverted_count: int
    detect_before: float
    detect_after: float
    detect_delta: float
    engine: str = "local"
    style: Style = "academic"
    language_usage: dict[str, str] = Field(default_factory=dict)
    changed_count: int = 0
    elapsed_ms: int = 0


class ProviderInfo(BaseModel):
    name: str
    model: str
    ready: bool
    is_default: bool
    language: str = "any"


class ProvidersResponse(BaseModel):
    providers: list[ProviderInfo]
    default: str
    routing: dict[str, str] = Field(default_factory=dict)
