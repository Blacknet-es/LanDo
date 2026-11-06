FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Suppress hardlink warnings when the cache and bind-mount are on different FSes
ENV UV_LINK_MODE=copy

# Install dependencies first (layer is cached unless pyproject.toml changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# Copy source
COPY src/ ./src/
COPY scripts/ ./scripts/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
