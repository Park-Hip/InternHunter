FROM python:3.12-slim

# Install system dependencies needed for Playwright and psycopg2
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv into a virtual environment
RUN uv sync --frozen --no-dev

# Activate the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Install playwright browsers and dependencies
RUN playwright install chromium
RUN playwright install-deps

# Copy application code
COPY . .

# Keep the container alive serving the Prefect flow schedule
CMD ["python", "-m", "src.scripts.deployment"]
