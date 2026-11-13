"""FastAPI 应用入口：自检报告、双语改写、单段重试、供应商查询 + 前端静态托管。"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import model_detector
from .ai_judge import analyze_with_model
from .config import settings
from .detector import analyze_text, detect_language, score_text
from .provider import LLMError
from .rewriter import proxy_detect, rewrite_paragraph, rewrite_text
from .schemas import (
    ClassifierVerdict,
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

@asynccontextmanager
async def lifespan(_: FastAPI):
    # 后台预热分类器：首次下载权重不阻塞 /api/detect；失败只降级，不影响启动
    model_detector.warmup()
    yield


app = FastAPI(title="AI 痕迹自检与润色工作台", version="0.3.0", lifespan=lifespan)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

SOURCE_NOTE = (
    "行文特征指数：由句长分布、词汇丰富度、套话密度与可枚举句式四类统计量加权得到，"
    "可复现、可追溯，用于写作自检与修订定位"
)


def _classifier_result(text: str, language: str) -> dict[str, Any]:
    """分类器疑似度：任何异常都降级，不影响规则信号返回。"""
    try:
        return model_detector.judge(text, language)
    except Exception as exc:  # pragma: no cover - 防御性兜底
        return {
            "available": False,
            "model": "",
            "label": "unavailable",
            "probability": 0.0,
            "note": f"分类器调用失败：{type(exc).__name__}: {exc}",
            "segments": [],
        }


@app.get("/api/health")
def health() -> dict[str, object]:
    ready = [n for n, p in settings.providers.items() if p.is_ready()]
    return {
        "status": "ok",
        "providers_ready": ready,
        "default_provider": settings.default_provider,
        "engines": ["local"] + (["llm"] if ready else []),
        "language_routing": settings.routing(),
        "classifier": model_detector.status(),
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

    if req.engine == "llm":
        cfg = settings.get_provider(settings.default_provider) or settings.get_provider_for_language(
            detect_language(req.text)
        )
        if cfg is None or not cfg.is_ready():
            raise HTTPException(
                status_code=502,
                detail="模型评估需要先配置可用的模型供应商（backend/providers.json 或环境变量）",
            )
        try:
            data = analyze_with_model(req.text, cfg)
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        data["classifier"] = _classifier_result(req.text, str(data.get("language", "zh")))
        return DetectResponse.model_validate(data)

    report = analyze_text(req.text)
    overall, segments = proxy_detect(req.text)
    language = str(report["language"])
    return DetectResponse(
        score=overall,
        source="proxy",
        source_note=SOURCE_NOTE,
        segments=[SegmentScore(index=i, text=t, score=s) for i, t, s in segments],
        language=language,
        metrics=[Metric(**m) for m in report["metrics"]],
        sentences=[SentenceRisk(**s) for s in report["sentences"]],
        high_risk_count=int(report["high_risk_count"]),
        pattern_hits=list(report["pattern_hits"]),
        caveat=str(report["caveat"]),
        stats=TextStats(**report["stats"]),
        classifier=ClassifierVerdict(**_classifier_result(req.text, language))
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
@app.post("/api/extract")
async def extract(file: UploadFile = File(...)) -> dict[str, object]:
    """解析上传的文档为纯文本：.txt/.md 直读，.docx 用 python-docx，.pdf 用 pypdf。"""
    name = (file.filename or "").lower()
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大（上限 15MB）")
    text = ""
    try:
        if name.endswith(".docx"):
            import io

            from docx import Document

            doc = Document(io.BytesIO(data))
            text = "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        elif name.endswith(".pdf"):
            import io

            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            pages = [(page.extract_text() or "").strip() for page in reader.pages]
            text = "\n\n".join(p for p in pages if p)
        elif name.endswith((".txt", ".md", ".markdown")):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("gbk", errors="replace")
        else:
            raise HTTPException(status_code=400, detail="仅支持 .txt / .md / .docx / .pdf")
    except HTTPException:
        raise
    except Exception as exc:  # 解析库抛出的任何异常都转为可读错误
        raise HTTPException(status_code=400, detail="解析失败：" + str(exc)) from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="未解析到文本内容（PDF 可能是扫描件，无文本层）")
    return {"text": text, "filename": file.filename, "chars": len(text)}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))
