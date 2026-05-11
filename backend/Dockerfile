FROM python:3.12-slim

WORKDIR /app

# mediapipe needs libGL, psycopg2 needs libpq, video needs ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Pull uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependency layer (cached unless pyproject.toml/uv.lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# App source
COPY . .

# Run migrations then start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]