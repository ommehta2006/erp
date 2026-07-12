FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8080 \
    APP_DATABASE=/app/data/factorypulse.sqlite3

WORKDIR /app
COPY . /app
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python scripts/smoke_test.py --base-url http://127.0.0.1:8080 --health-only
CMD ["python", "-m", "backend.factory_erp.app"]
