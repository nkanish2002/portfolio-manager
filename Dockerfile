# ── Stage 1: Build React frontend ─────────────────────────────────────
FROM docker.io/library/node:22-alpine AS frontend-builder

WORKDIR /app

# Copy frontend deps first (layer caching)
COPY frontend/package.json frontend/package-lock.json ./frontend/

# Install frontend deps
WORKDIR /app/frontend
RUN npm ci --ignore-scripts

# Copy full frontend source + minimal src/ tree (vite outputs to ../src/portfolio_manager/static)
COPY frontend/src ./src
COPY frontend/vite.config.ts frontend/tsconfig.json frontend/index.html ./

# Ensure the outDir parent exists so vite build succeeds
RUN mkdir -p /app/src/portfolio_manager

# Build frontend → outputs to ../src/portfolio_manager/static
RUN npm run build

# ── Stage 2: Python runtime ───────────────────────────────────────────
FROM docker.io/python:3.14-slim AS runtime

# Install uv for dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency manifests first (layer caching for deps)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy backend source (needed before editable install)
COPY src ./src

# Install the project in editable mode so `import portfolio_manager` works
RUN uv pip install -e .

# Copy frontend build artifacts (overlays static/ inside the package)
COPY --from=frontend-builder /app/src/portfolio_manager/static ./src/portfolio_manager/static

# Copy migrations config
COPY alembic.ini ./
COPY migrations/ ./migrations/
# Copy Dynaconf settings (needed for settings.DEBUG, settings.DATABASE_URL, etc.)
COPY settings.yaml ./

# Set path so uv run works
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run alembic upgrade + start uvicorn
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn portfolio_manager.main:app --host 0.0.0.0 --port 8000 --loop uvloop"]
