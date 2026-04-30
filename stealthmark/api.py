import sys
from pathlib import Path

# 将项目 src 目录加入 path，使 from src.core 导入正常工作
_src = str(Path(__file__).resolve().parent.parent / 'src')
if _src not in sys.path:
    sys.path.insert(0, _src)

import os
import tempfile
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.core.manager import StealthMark
from src.core.base import WatermarkStatus

sm = StealthMark()

app = FastAPI(
    title="StealthMark API",
    description="隐式水印工具 - Web API",
    version="1.0.0",
)


# ==================== Pydantic Models ====================

class EmbedResponse(BaseModel):
    success: bool
    watermark: str
    output_file: Optional[str] = None
    message: str


class ExtractResponse(BaseModel):
    success: bool
    watermark: Optional[str] = None
    format: str
    message: str


class VerifyResponse(BaseModel):
    success: bool
    match: bool
    extracted: Optional[str] = None
    expected: str
    match_score: float


class BatchFileResult(BaseModel):
    filename: str
    success: bool
    message: str
    watermark: Optional[str] = None
    match: Optional[bool] = None


class BatchResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: List[BatchFileResult]


class InfoResponse(BaseModel):
    handlers: int
    formats: dict


SUPPORTED_CATEGORIES = {
    "document": ["pdf", "docx", "pptx", "xlsx", "odt", "odp", "ods", "epub", "rtf"],
    "image": ["png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp", "gif", "heic", "heif"],
    "audio": ["wav", "mp3", "flac", "aac", "m4a"],
    "video": ["mp4", "avi", "mkv", "mov", "webm", "wmv"],
}


async def save_upload(file: UploadFile, suffix: str = "") -> str:
    suffix = suffix or Path(file.filename or "").suffix
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return path


# ==================== Endpoints ====================

@app.get("/")
async def root():
    return {
        "name": "StealthMark API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "info": "/info",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "handlers": len(sm._handler_registry)}


@app.get("/info", response_model=InfoResponse)
async def info():
    formats = {}
    all_exts = set(sm.supported_formats())
    for cat, exts in SUPPORTED_CATEGORIES.items():
        found = [f".{e}" for e in exts if f".{e}" in all_exts]
        if found:
            formats[cat] = found
    return InfoResponse(handlers=len(sm._handler_registry), formats=formats)


@app.post("/embed", response_model=EmbedResponse)
async def embed_api(
    file: UploadFile = File(...),
    watermark: str = Form(...),
    password: Optional[str] = Form(None),
):
    if not watermark:
        raise HTTPException(400, "watermark is required")

    suffix = Path(file.filename or "").suffix
    input_path = await save_upload(file, suffix)
    out_fd, output_path = tempfile.mkstemp(suffix=suffix)
    os.close(out_fd)

    try:
        result = sm.embed(input_path, watermark, output_path, password=password)
        if result.is_success:
            return EmbedResponse(
                success=True,
                watermark=watermark,
                output_file=output_path,
                message="嵌入成功",
            )
        else:
            return EmbedResponse(
                success=False,
                watermark=watermark,
                message=f"嵌入失败: {result.message}",
            )
    finally:
        try:
            os.unlink(input_path)
        except OSError:
            pass


@app.post("/extract", response_model=ExtractResponse)
async def extract_api(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
):
    suffix = Path(file.filename or "").suffix
    input_path = await save_upload(file, suffix)

    try:
        result = sm.extract(input_path, password=password)
        if result.is_success and result.watermark:
            return ExtractResponse(
                success=True,
                watermark=result.watermark.content,
                format=suffix,
                message="提取成功",
            )
        else:
            return ExtractResponse(
                success=False,
                format=suffix,
                message=f"提取失败: {result.message}",
            )
    finally:
        try:
            os.unlink(input_path)
        except OSError:
            pass


@app.post("/verify", response_model=VerifyResponse)
async def verify_api(
    file: UploadFile = File(...),
    watermark: str = Form(...),
    password: Optional[str] = Form(None),
):
    if not watermark:
        raise HTTPException(400, "watermark is required")

    suffix = Path(file.filename or "").suffix
    input_path = await save_upload(file, suffix)

    try:
        result = sm.verify(input_path, watermark, password=password)
        return VerifyResponse(
            success=result.is_success,
            match=result.is_valid,
            extracted=result.details.get("extracted") if result.details else None,
            expected=watermark,
            match_score=result.match_score,
        )
    finally:
        try:
            os.unlink(input_path)
        except OSError:
            pass


@app.post("/batch", response_model=BatchResponse)
async def batch_api(
    files: List[UploadFile] = File(...),
    watermark: str = Form(...),
    action: str = Form("embed"),
    password: Optional[str] = Form(None),
):
    if action not in ("embed", "extract", "verify"):
        raise HTTPException(400, "action must be 'embed', 'extract', or 'verify'")

    results = []
    for file in files:
        suffix = Path(file.filename or "").suffix
        input_path = await save_upload(file, suffix)
        out_fd, output_path = tempfile.mkstemp(suffix=suffix)
        os.close(out_fd)

        try:
            if action == "embed":
                r = sm.embed(input_path, watermark, output_path, password=password)
                results.append(BatchFileResult(
                    filename=file.filename or "?",
                    success=r.is_success,
                    message=r.message,
                    watermark=watermark,
                ))
            elif action == "extract":
                r = sm.extract(input_path, password=password)
                results.append(BatchFileResult(
                    filename=file.filename or "?",
                    success=r.is_success,
                    message=r.message,
                    watermark=r.watermark.content if r.watermark else None,
                ))
            else:
                r = sm.verify(input_path, watermark, password=password)
                results.append(BatchFileResult(
                    filename=file.filename or "?",
                    success=r.is_success,
                    message=r.message,
                    watermark=r.details.get("extracted") if r.details else None,
                    match=r.is_valid,
                ))
        except Exception as e:
            results.append(BatchFileResult(
                filename=file.filename or "?",
                success=False,
                message=str(e),
            ))
        finally:
            try:
                os.unlink(input_path)
            except OSError:
                pass
            try:
                os.unlink(output_path)
            except OSError:
                pass

    success_count = sum(1 for r in results if r.success)
    return BatchResponse(
        total=len(results),
        success=success_count,
        failed=len(results) - success_count,
        results=results,
    )
