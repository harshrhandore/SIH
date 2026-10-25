FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/workspace/apps/api:/workspace
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 tesseract-ocr tesseract-ocr-eng libmagic1 libglib2.0-0 postgresql-client && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY apps/api/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY apps/api/app /workspace/apps/api/app
COPY apps/api/alembic /workspace/apps/api/alembic
COPY apps/api/alembic.ini /workspace/apps/api/alembic.ini
COPY db /workspace/db
COPY scripts /workspace/scripts
COPY fixtures /workspace/fixtures
RUN useradd --uid 10001 --create-home ledger && mkdir -p /storage && chown 10001:10001 /storage /workspace/fixtures
WORKDIR /workspace/apps/api
USER 10001
FROM base AS test
USER root
COPY apps/api/requirements-dev.lock /tmp/dev.lock
RUN pip install --no-cache-dir -r /tmp/dev.lock
COPY apps/api/tests /workspace/apps/api/tests
COPY apps/api/pyproject.toml /workspace/apps/api/pyproject.toml
USER 10001
FROM base AS runtime
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
