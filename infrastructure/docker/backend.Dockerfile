FROM ghcr.io/astral-sh/uv:0.5.14-python3.12-bookworm-slim AS builder

WORKDIR /app/apps/backend
COPY apps/backend/pyproject.toml apps/backend/uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY apps/backend /app/apps/backend
RUN uv sync --frozen --no-dev || uv sync --no-dev

FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/apps/backend/.venv/bin:$PATH"

RUN groupadd -r viraldy && useradd -r -g viraldy viraldy
WORKDIR /app

COPY --from=builder --chown=viraldy:viraldy /app/apps/backend /app/apps/backend
USER viraldy

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

WORKDIR /app/apps/backend
CMD ["uvicorn", "viraldy.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
