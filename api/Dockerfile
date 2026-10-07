# One image definition, two targets:
#   dev   - used by docker-compose.yml on your laptop (code is mounted in, reloads on save)
#   prod  - used by deploy/docker-compose.prod.yml (code baked in, runs as a non-root user)
FROM python:3.12-slim AS base

# uv installs Python packages from the exact versions pinned in uv.lock.
RUN pip install --no-cache-dir uv

# Keep the virtualenv outside /app so mounting the source code over /app in
# development does not hide the installed packages.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies before copying the code, so Docker can reuse this layer
# when only the code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project


FROM base AS dev
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]


FROM base AS prod
# Production installs no test or lint tools.
RUN uv sync --frozen --no-install-project --no-dev

# Run as an ordinary user: if the app were ever broken into, the attacker
# wouldn't be root inside the container.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data/uploads \
    && chown -R app:app /data
COPY --chown=app:app . .
USER app

EXPOSE 8000
# The production compose file sets the command for each service (API, worker,
# scheduler, migrations); this default runs the API.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
