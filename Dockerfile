# === StealthMark Docker ===
# Multi-stage build: builder (deps) + runtime (minimal image)

# Stage 1: Builder — installs all dependencies
FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir pip && \
    /opt/venv/bin/pip install --no-cache-dir -e ".[api]"

# Stage 2: Runtime — minimal image
FROM python:3.12-slim

# ffmpeg: required by video/audio handlers (imageio-ffmpeg also bundles its own, but some handlers need system ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtualenv from builder (includes all Python deps)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code and install package
COPY src/ ./src/
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[api]"

# Static file storage
ENV STEALTHMARK_FILE_DIR=/app/static/file
ENV STEALTHMARK_RETENTION_DAYS=90
RUN mkdir -p /app/static/file

# Default: run API server
EXPOSE 8000
ENTRYPOINT ["uvicorn"]
CMD ["stealthmark.api:app", "--host", "0.0.0.0", "--port", "8000"]
