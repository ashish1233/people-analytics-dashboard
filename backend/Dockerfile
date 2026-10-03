# Copied unchanged from templates/web/backend. The only app-specific line is the
# module path in CMD.
FROM python:3.12-slim AS base

# Non-root from the start. The container never needs to write to its own
# filesystem: configuration arrives as environment variables (see .env.example)
# and nothing is persisted locally — the audit buffer in the SDK is in-memory by
# design, because a buffer that survives a restart is a copy of access records
# outside the audit store ADR-4 puts beyond the platform team's reach.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir . \
    && chown -R appuser:appuser /srv/app

USER appuser

EXPOSE 8000

# ADR-3: every app answers the same health shape, and the operator view in ADR-4
# is built on that. The SDK registers /health; do not shadow it.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "dashboard.main:app", "--host", "0.0.0.0", "--port", "8000"]
