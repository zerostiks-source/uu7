"""FastAPI 应用入口：自检报告、双语改写、单段重试、供应商查询 + 前端静态托管。"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .detector import analyze_text, detect_language, score_text
from .provider import LLMError
from .rewriter import proxy_detect, rewrite_paragraph, rewrite_text
from .schemas import (
    DetectRequest,
    DetectResponse,
    Metric,
    ProviderInfo,
    ProvidersResponse,
    RewriteRequest,
    RewriteResponse,
    RewriteSegmentRequest,
    RewriteSegmentResponse,
    SegmentScore,
    SentenceRisk,
    TextStats,
)

app = FastAPI(title="AI 痕迹自检与润色工作台", version="0.3.0")

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

SOURCE_NOTE = (
    "启发式模板化信号：基于句长分布、用词重复、套话与可枚举句式估算，仅供写作参考；"
    "不判定文本是否由 AI 生成，与知网/维普/Turnitin 等官方检测结果不可比"
)


@app.get("/api/health")
def health() -> dict[str, object]:
    ready = [n for n, p in settings.providers.items() if p.is_ready()]
    return {
        "status": "ok",
        "providers_ready": ready,
        "default_provider": settings.default_provider,
        "engines": ["local"] + (["llm"] if ready else []),
        "language_routing": settings.routing(),
        "version": "0.3.0",
    }


@app.get("/api/providers", response_model=ProvidersResponse)
def list_providers() -> ProvidersResponse:
    items = [
        ProviderInfo(
            name=cfg.name,
            model=cfg.model,
            ready=cfg.is_ready(),
            is_default=(cfg.name == settings.default_provider),
            language=cfg.language,
        )
        for cfg in settings.providers.values()
    ]
    return ProvidersResponse(
        providers=items, default=settings.default_provider, routing=settings.routing()
    )


@app.post("/api/detect", response_model=DetectResponse)
def detect(req: DetectRequest) -> DetectResponse:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="无有效内容可检测")

    report = analyze_text(req.text)
    overall, segments = proxy_detect(req.text)
    return DetectResponse(
        score=overall,
        source="proxy",
        source_note=SOURCE_NOTE,
        segments=[SegmentScore(index=i, text=t, score=s) for i, t, s in segments],
        language=str(report["language"]),
        metrics=[Metric(**m) for m in report["metrics"]],  # type: ignore[arg-type]
        sentences=[SentenceRisk(**s) for s in report["sentences"]],  # type: ignore[arg-type]
        high_risk_count=int(report["high_risk_count"]),
        pattern_hits=list(report["pattern_hits"]),  # type: ignore[arg-type]
        caveat=str(report["caveat"]),
        stats=TextStats(**report["stats"]),  # type: ignore[arg-type]
    )


@app.post("/api/rewrite", response_model=RewriteResponse)
def rewrite(req: RewriteRequest) -> RewriteResponse:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="无有效内容可改写")
    started = time.perf_counter()
    before = score_text(req.text)
    try:
        segments, provider_name, engine_name = rewrite_text(
            req.text,
            req.strength,
            req.provider,
            engine=req.engine,
            style=req.style,
            glossary=req.glossary,
            only_high_risk=req.only_high_risk,
            high_risk_threshold=req.high_risk_threshold,
            variant=req.variant,
            language=req.language,
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    after = score_text("\n\n".join(s.rewritten for s in segments))
    failed = sum(1 for s in segments if s.status == "failed")
    reverted = sum(1 for s in segments if s.status == "reverted")
    changed = sum(1 for s in segments if s.changed)
    language_usage: dict[str, str] = {}
    for seg in segments:
        language_usage.setdefault(seg.language, seg.provider)
    return RewriteResponse(
        strength=req.strength,
        provider=provider_name,
        segments=segments,
        failed_count=failed,
        reverted_count=reverted,
        detect_before=before,
        detect_after=after,
        detect_delta=round(before - after, 1),
        engine=engine_name,
        style=req.style,
        language_usage=language_usage,
        changed_count=changed,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )


@app.post("/api/rewrite-segment", response_model=RewriteSegmentResponse)
def rewrite_segment(req: RewriteSegmentRequest) -> RewriteSegmentResponse:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="无有效内容可改写")
    language = detect_language(req.text) if req.language == "auto" else req.language
    try:
        text, engine_name, locked = rewrite_paragraph(
            req.text,
            req.strength,
            req.provider,
            engine=req.engine,
            style=req.style,
            glossary=req.glossary,
            variant=req.variant,
            language=req.language,
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RewriteSegmentResponse(
        text=text, engine=engine_name, language=language, locked_spans=locked
    )


# 静态托管前端（单页）
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))
