import os
import uuid
import time
import shutil
import threading
import tempfile
import configparser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core.manager import StealthMark
from .core.base import WatermarkStatus

sm = StealthMark()

from stealthmark import __version__

app = FastAPI(
    title="StealthMark API",
    description="隐式水印工具 - Web API",
    version=__version__,
)

# Mount static files for test frontend
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ==================== Configuration ====================

def _load_config() -> configparser.ConfigParser:
    """Load config from config.ini, searching multiple locations."""
    cfg = configparser.ConfigParser()
    
    # Search paths: 1) CWD 2) same dir as api.py's parent (project root) 3) api.py's dir
    _api_dir = Path(__file__).resolve().parent
    _project_root = _api_dir.parent.parent  # src/stealthmark/ -> src/ -> project root
    
    search_paths = [
        Path.cwd() / "config.ini",
        _project_root / "config.ini",
        _api_dir / "config.ini",
    ]
    
    for p in search_paths:
        if p.exists():
            cfg.read(str(p), encoding="utf-8")
            break
    
    return cfg


_config = _load_config()


def _cfg(section: str, key: str, fallback: str = "") -> str:
    """Get config value: config.ini first, then env variable STEALTHMARK_<KEY>, then fallback."""
    ini_val = _config.get(section, key, fallback="")
    env_key = f"STEALTHMARK_{key.upper()}"
    env_val = os.environ.get(env_key, "")
    # Env variable overrides config.ini
    return env_val or ini_val or fallback


# ==================== File Store (Date-based directory, configurable retention) ====================

FILE_BASE_DIR = Path(_cfg("file_storage", "base_dir", str(Path(__file__).resolve().parent / "static" / "file")))
# Resolve relative paths against api.py's directory
if not FILE_BASE_DIR.is_absolute():
    FILE_BASE_DIR = Path(__file__).resolve().parent / FILE_BASE_DIR

FILE_RETENTION_DAYS = int(_cfg("file_storage", "retention_days", "90"))  # 0 = permanent
FILE_CLEANUP_INTERVAL = int(_cfg("file_storage", "cleanup_interval", "3600"))  # seconds


class FileStore:
    """Date-based file storage with configurable retention.

    Directory layout: <FILE_BASE_DIR>/<YYYY>/<M>/<uuid><ext>
    Example: static/file/2026/5/a1b2c3d4.pdf

    Retention:
    - Default: 90 days (3 months), files older than this are auto-deleted
    - Set retention_days=0 in config.ini for permanent storage
    - Individual files can be marked permanent at registration time

    Cleanup:
    - Background thread scans file directories every cleanup_interval seconds
    - Removes files whose directory date (YYYY/M) is older than retention period
    - Empty year/month directories are pruned after file removal
    """

    def __init__(
        self,
        base_dir: Path = FILE_BASE_DIR,
        retention_days: int = FILE_RETENTION_DAYS,
        cleanup_interval: int = FILE_CLEANUP_INTERVAL,
    ):
        self._base_dir = Path(base_dir)
        self._retention_days = retention_days
        self._lock = threading.Lock()
        self._registry: dict[str, dict] = {}  # uuid -> {path, created_at, permanent}
        self._running = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_interval = cleanup_interval

        # Ensure base directory exists
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def retention_days(self) -> int:
        return self._retention_days

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def start_cleanup(self):
        """Start background cleanup thread."""
        if self._retention_days == 0:
            return  # Permanent mode, no cleanup needed
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def stop_cleanup(self):
        """Stop background cleanup thread."""
        self._running = False

    def _cleanup_loop(self):
        while self._running:
            time.sleep(self._cleanup_interval)
            self.cleanup_expired()

    def _date_dir(self, dt: Optional[datetime] = None) -> Path:
        """Get date-based directory path: base_dir/YYYY/M"""
        dt = dt or datetime.now()
        return self._base_dir / str(dt.year) / str(dt.month)

    def register(self, src_path: str, original_name: str = "", permanent: bool = False) -> str:
        """Move file into date-based storage and return UUID token.

        Args:
            src_path: Source file path (will be moved, not copied)
            original_name: Original filename to derive extension
            permanent: If True, file is never auto-deleted

        Returns:
            UUID token for later retrieval
        """
        file_id = uuid.uuid4().hex
        now = datetime.now()
        date_dir = self._date_dir(now)
        date_dir.mkdir(parents=True, exist_ok=True)

        # Build destination path: date_dir/<uuid><ext>
        ext = Path(original_name).suffix if original_name else Path(src_path).suffix
        dest_path = date_dir / f"{file_id}{ext}"

        # Move file from temp location to managed storage
        shutil.move(str(src_path), str(dest_path))

        with self._lock:
            self._registry[file_id] = {
                "path": str(dest_path),
                "created_at": time.time(),
                "permanent": permanent,
                "date_dir": str(date_dir),
            }
        return file_id

    def get(self, file_id: str) -> Optional[str]:
        """Get file path by UUID. Returns None if not found."""
        with self._lock:
            entry = self._registry.get(file_id)
            if entry is None:
                return None
            path = entry["path"]
            if not Path(path).exists():
                self._registry.pop(file_id, None)
                return None
            return path

    def mark_permanent(self, file_id: str) -> bool:
        """Mark a file as permanent (never auto-deleted). Returns False if not found."""
        with self._lock:
            entry = self._registry.get(file_id)
            if entry is None:
                return False
            entry["permanent"] = True
            return True

    def cleanup_expired(self):
        """Remove files older than retention period, skip permanent ones."""
        if self._retention_days == 0:
            return  # Permanent mode

        cutoff = datetime.now() - timedelta(days=self._retention_days)
        cutoff_year, cutoff_month = cutoff.year, cutoff.month

        with self._lock:
            # Find expired registry entries
            expired_ids = []
            for fid, entry in self._registry.items():
                if entry.get("permanent"):
                    continue
                date_dir = Path(entry["date_dir"])
                try:
                    # Parse year/month from directory path
                    parts = date_dir.parts
                    year = int(parts[-2])
                    month = int(parts[-1])
                    if (year, month) < (cutoff_year, cutoff_month):
                        expired_ids.append(fid)
                except (ValueError, IndexError):
                    pass

            for fid in expired_ids:
                entry = self._registry.pop(fid, {})
                try:
                    os.unlink(entry.get("path", ""))
                except OSError:
                    pass

        # Prune empty date directories
        self._prune_empty_dirs()

    def _prune_empty_dirs(self):
        """Remove empty month and year directories."""
        if not self._base_dir.exists():
            return
        for year_dir in self._base_dir.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in list(year_dir.iterdir()):
                if month_dir.is_dir() and not any(month_dir.iterdir()):
                    try:
                        month_dir.rmdir()
                    except OSError:
                        pass
            if year_dir.is_dir() and not any(year_dir.iterdir()):
                try:
                    year_dir.rmdir()
                except OSError:
                    pass

    def cleanup_all(self):
        """Remove all files (for shutdown). Only removes non-permanent files."""
        with self._lock:
            for fid, entry in list(self._registry.items()):
                if entry.get("permanent"):
                    continue
                try:
                    os.unlink(entry.get("path", ""))
                except OSError:
                    pass
                self._registry.pop(fid, None)


# Global file store instance
file_store = FileStore()
file_store.start_cleanup()


@app.on_event("shutdown")
async def shutdown_event():
    file_store.stop_cleanup()


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
    """Save uploaded file to a temp location for processing."""
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
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "info": "/info",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "handlers": len(sm._handler_registry),
        "file_storage": str(file_store.base_dir),
        "retention_days": file_store.retention_days,
    }


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
        if f.is_file() and f.name.startswith("test.") and not f.name.startswith("test_wav"):
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
        raise HTTPException(404, "File not found or expired.")
    
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
    permanent: bool = Form(False),
):
    """Embed watermark into file.

    Args:
        permanent: If True, file is stored permanently (not auto-deleted after retention period).
    """
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
            file_id = file_store.register(actual_output, original_name=Path(file.filename or "").name, permanent=permanent)
            return EmbedResponse(
                success=True,
                watermark=watermark,
                file_id=file_id,
                filename=Path(file.filename or "").name,
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
    permanent: bool = Form(False),
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
                    file_id = file_store.register(actual_output, original_name=file.filename or "", permanent=permanent)
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
