# Image for the Zer0 sales agent on Cloud Run.
# Built and deployed by .github/workflows/deploy.yml.
# Stage 1: build the Next.js frontend into a static export (frontend/out).
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the Flask app, which also serves the export.
FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# The app reads prompts/, templates/ and static/ relative to this directory.
# .dockerignore keeps tests, docs, scripts and local files out.
COPY . .

# The built frontend. Flask serves it for every path that no API route matches (web/).
COPY --from=web /web/out /app/frontend_out

# Run as an unprivileged user.
RUN useradd --system --uid 10001 app && chown -R app /app
USER app

# Cloud Run sets PORT (8080 by default).
ENV PORT=8080
EXPOSE 8080

# One worker process: the DB pool is deliberately tiny (DB_POOL_MAX_SIZE=2)
# and the in-memory state (scheduler, locks) is per process. Threads give the
# concurrency; requests spend their time waiting on the LLM, not on CPU.
# --timeout 0: Cloud Run enforces the request timeout itself.
CMD exec gunicorn --bind ":${PORT}" --workers 1 --threads 8 --timeout 0 \
    --access-logfile - --error-logfile - app:app
