# Multi-stage build for portfolio-manager TUI
# Stage 1: Build Python dependencies for TUI
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder-tui
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY src/ ./src/

# Stage 1b: Build textual-web in a separate env (incompatible textual version)
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder-web
RUN uv venv /opt/web-venv && \
    . /opt/web-venv/bin/activate && \
    uv pip install textual-web>=0.8.0

# Stage 2: Runtime image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    ncurses-term \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies for TUI
COPY --from=builder-tui /app/.venv /app/.venv
# Copy Python source
COPY --from=builder-tui /app/src /app/src
# Copy migrations
COPY migrations /app/migrations
# Copy textual-web config
COPY textual-web.toml /app/textual-web.toml
# Copy textual-web (separate venv due to incompatible textual version)
COPY --from=builder-web /opt/web-venv /opt/web-venv

# Set environment variables
ENV PATH="/app/.venv/bin:/opt/web-venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/src"
ENV DATABASE_URL="sqlite+aiosqlite:///data/portfolio.db"
ENV TERM="xterm-256color"

# Create data directory for persistent storage
RUN mkdir -p /app/data && chmod 777 /app/data

# Default: run as CLI TUI
# Override with: docker run --tty --interactive portfolio-manager
# Or web mode: docker run -p 8080:8080 portfolio-manager --web
CMD ["uv", "run", "textual", "portfolio_manager"]
