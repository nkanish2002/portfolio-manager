# Multi-stage build for portfolio-manager TUI
# Stage 1: Build Python dependencies
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY src/ ./src/

# Stage 2: Runtime image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    ncurses-term \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies
COPY --from=builder /app/.venv /app/.venv
# Copy Python source
COPY --from=builder /app/src /app/src
# Copy migrations
COPY migrations /app/migrations

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/src"
ENV DATABASE_URL="sqlite+aiosqlite:///data/portfolio.db"
ENV TERM="xterm-256color"

# Create data directory for persistent storage
RUN mkdir -p /app/data && chmod 777 /app/data

ENTRYPOINT ["uv", "run", "textual", "portfolio_manager"]
