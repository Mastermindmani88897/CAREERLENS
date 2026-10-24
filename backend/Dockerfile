# =============================================================================
# CareerLens — Production Backend Dockerfile
# Multi-stage build with non-root security and pre-cached offline embeddings
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build virtual environment and pre-cache model
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install compilation build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create isolated Python virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-cache local sentence-transformers embedding model for fast offline startup
ENV HF_HOME=/opt/cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# -----------------------------------------------------------------------------
# Stage 2: Minimal Production Runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runner

# Install minimal runtime dependencies (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root unprivileged service account
RUN groupadd -g 10001 careerlens && \
    useradd -u 10001 -g careerlens -m -s /bin/bash careerlens

WORKDIR /app

# Copy virtual environment and pre-cached embeddings from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=careerlens:careerlens /opt/cache/huggingface /app/.cache/huggingface

# Environment configuration
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    RESUME_UPLOAD_DIR=/app/data/uploads/resumes

# Prepare writable directories for non-root user
RUN mkdir -p /app/data/uploads/resumes && \
    chown -R careerlens:careerlens /app

# Copy application source code and migration scripts with appropriate ownership
COPY --chown=careerlens:careerlens app /app/app
COPY --chown=careerlens:careerlens alembic /app/alembic
COPY --chown=careerlens:careerlens alembic.ini /app/alembic.ini
COPY --chown=careerlens:careerlens pyproject.toml /app/pyproject.toml

# Switch to non-root execution
USER careerlens

# Expose internal backend application port
EXPOSE 8000

# Container health probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default entrypoint runs FastAPI with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
