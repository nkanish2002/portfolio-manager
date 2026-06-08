# Multi-stage build for portfolio-manager
# Stage 1: Build frontend (React SPA)
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Python dependencies
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY src/ ./src/

# Stage 3: Runtime image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies
COPY --from=builder /app/.venv /app/.venv
# Copy Python source
COPY --from=builder /app/src /app/src
# Copy React SPA build
COPY --from=frontend-builder /app/dist /app/frontend/dist

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/src"
ENV DATABASE_URL="sqlite+aiosqlite:///data/portfolio.db"

# Create data directory for persistent storage
RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 8000

CMD ["uvicorn", "portfolio_manager.main:app", "--host", "0.0.0.0", "--port", "8000"]
