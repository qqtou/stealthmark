# === StealthMark Docker ===
# Multi-stage build: builder + runtime

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages in a virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
RUN pip install --no-cache-dir "pip>=23.0" && \
    pip install --no-cache-dir -e ".[all]"

# Stage 2: Runtime
FROM python:3.12-slim

LABEL org.opencontainers.image.title="StealthMark"
LABEL org.opencontainers.image.description="跨格式隐形水印工具"
LABEL org.opencontainers.image.source="https://github.com/qqtou/stealthmark"

# Install runtime dependencies only (no ffmpeg source needed at runtime)
# imageio-ffmpeg bundles its own ffmpeg binary, so no system ffmpeg needed for most handlers
# However, some handlers (WMV/OGG) may need system ffmpeg, include it for completeness
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application
COPY --from=builder /app/src ./src

# Default command
ENTRYPOINT ["stealthmark"]
CMD ["--help"]