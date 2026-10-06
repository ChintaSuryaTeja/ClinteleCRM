FROM python:3.12-slim

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

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
