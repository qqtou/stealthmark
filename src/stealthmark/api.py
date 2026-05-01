import os
import uuid
import time
import tempfile
import threading
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core.manager import StealthMark
from .core.base import WatermarkStatus

sm = StealthMark()

app = FastAPI(
    title="StealthMark API",
    description="隐式水印工具 - Web API",
    version="1.1.0",
)

# Mount static files for test frontend
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ==================== File Store (UUID-based, auto-cleanup) ====================

class FileStore:
    """UUID-based file registry with TTL auto-cleanup.
    
    Replaces raw temp path exposure to prevent:
    1. Path traversal attacks (only registered files accessible)
    2. Temp file leaks (auto-cleanup after TTL)
    3. Stale references after restart (all refs are UUIDs)
    """

    def __init__(self, ttl_seconds: int = 3600, cleanup_interval: int = 300):
        self._store: dict[str, dict] = {}  # uuid -> {path, created_at}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._cleanup_interval = cleanup_interval

    def start_cleanup(self):
        """Start background cleanup thread."""
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def stop_cleanup(self):
        """Stop background cleanup thread."""
        self._running = False

    def _cleanup_loop(self):
        while self._running:
            time.sleep(self._cleanup_interval)
            self.remove_expired()

    def register(self, path: str) -> str:
        """Register a file path, return UUID token."""
        file_id = uuid.uuid4().hex
        with self._lock:
            self._store[file_id] = {
                "path": path,
                "created_at": time.time(),
            }
        return file_id

    def get(self, file_id: str) -> Optional[str]:
        """Get file path by UUID. Returns None if not found or expired."""
        with self._lock:
            entry = self._store.get(file_id)
            if entry is None:
                return None
            if time.time() - entry["created_at"] > self._ttl:
                self._remove_file(file_id, entry)
                return None
            return entry["path"]

    def _remove_file(self, file_id: str, entry: dict):
        """Remove file from disk and store. Must be called within lock."""
        self._store.pop(file_id, None)
        try:
            os.unlink(entry["path"])
        except OSError:
            pass

    def remove_expired(self):
        """Remove all expired files."""
        now = time.time()
        with self._lock:
            expired = [
                fid for fid, entry in self._store.items()
                if now - entry["created_at"] > self._ttl
            ]
            for fid in expired:
                self._remove_file(fid, self._store.get(fid, {}))

    def cleanup_all(self):
        """Remove all registered files (for shutdown)."""
        with self._lock:
            for fid, entry in list(self._store.items()):
                try:
                    os.unlink(entry["path"])
                except OSError:
                    pass
            self._store.clear()


# Global file store instance
file_store = FileStore(ttl_seconds=3600, cleanup_interval=300)
file_store.start_cleanup()


@app.on_event("shutdown")
async def shutdown_event():
    file_store.stop_cleanup()
    file_store.cleanup_all()


# ==================== Pydantic Models ====================

class EmbedResponse(BaseModel):
    success: bool
    watermark: str
    file_id: Optional[str] = None   # UUID token for download
    filename: Optional[str] = None   # Original filename for download
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
    file_id: Optional[str] = None    # UUID token for embed results


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
    "audio": ["wav", "mp3", "flac", "aac", "m4a", "ogg"],
    "video": ["mp4", "avi", "mkv", "mov", "webm", "wmv"],
}

# Test template files directory
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"


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
        "version": "1.1.0",
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


@app.get("/test")
async def test_page():
    """Redirect to test frontend page."""
    _html_path = Path(__file__).resolve().parent / "static" / "test.html"
    if _html_path.exists():
        return HTMLResponse(content=_html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Test page not found</h1><p>Run: python -m stealthmark.api</p>", status_code=404)


@app.get("/test-templates")
async def test_templates():
    """List available test template files."""
    if not FIXTURES_DIR.exists():
        return {"templates": [], "error": "Fixtures directory not found"}
    
    templates = []
    for f in FIXTURES_DIR.iterdir():
        if f.is_file() and f.name.startswith("test."):
            templates.append({
                "name": f.name,
                "ext": f.suffix,
                "size": f.stat().st_size,
                "url": f"/test-template/{f.suffix[1:]}",
            })
    return {"templates": templates}


@app.get("/test-template/{ext}")
async def get_test_template(ext: str):
    """Download a test template file by extension."""
    ext_map = {
        "jpg": "jpeg",
        "jpeg": "jpeg",
        "tiff": "tiff",
        "tif": "tiff",
        "heif": "heic",
        "m4a": "m4a",
    }
    filename = f"test.{ext_map.get(ext, ext)}"
    filepath = FIXTURES_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(404, f"Template not found: {filename}")
    
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/octet-stream",
    )


# ==================== Output File Endpoint (UUID-based) ====================

@app.get("/output-file/{file_id}")
async def get_output_file(file_id: str):
    """Download output file by UUID token. Only registered files are accessible."""
    path = file_store.get(file_id)
    if path is None:
        raise HTTPException(404, "File not found or expired. Files are kept for 1 hour after creation.")
    
    filepath = Path(path)
    if not filepath.exists():
        raise HTTPException(404, "File has been deleted from disk.")
    
    return FileResponse(
        path=str(filepath),
        filename=filepath.name,
        media_type="application/octet-stream",
    )


# ==================== Embed/Extract/Verify Endpoints ====================

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
            actual_output = result.output_path if result.output_path else output_path
            file_id = file_store.register(actual_output)
            return EmbedResponse(
                success=True,
                watermark=watermark,
                file_id=file_id,
                filename=Path(actual_output).name,
                message="嵌入成功",
            )
        else:
            # Clean up failed output
            try:
                os.unlink(output_path)
            except OSError:
                pass
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
                file_id = None
                if r.is_success:
                    actual_output = r.output_path if r.output_path else output_path
                    file_id = file_store.register(actual_output)
                else:
                    try:
                        os.unlink(output_path)
                    except OSError:
                        pass
                results.append(BatchFileResult(
                    filename=file.filename or "?",
                    success=r.is_success,
                    message=r.message,
                    watermark=watermark,
                    file_id=file_id,
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
            try:
                os.unlink(output_path)
            except OSError:
                pass
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

    success_count = sum(1 for r in results if r.success)
    return BatchResponse(
        total=len(results),
        success=success_count,
        failed=len(results) - success_count,
        results=results,
    )
