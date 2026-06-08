# Multi-stage build for portfolio-manager
# Stage 1: Build dependencies
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy pyproject.toml and uv.lock for dependency installation
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-install-project

# Copy project source
COPY src/ ./src/

# Stage 2: Runtime image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Install system dependencies (for numpy, pandas, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /app/.venv /app/.venv
# Copy project source
COPY --from=builder /app/src /app/src

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/src"
ENV DATABASE_URL="sqlite+aiosqlite:///data/portfolio.db"

# Create data directory for persistent storage
RUN mkdir -p /app/data && chmod 777 /app/data

# Expose port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "portfolio_manager.main:app", "--host", "0.0.0.0", "--port", "8000"]
