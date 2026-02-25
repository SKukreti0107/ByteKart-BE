# Use a slim Python 3.12 image
FROM python:3.12-slim

# The official uv image provides the uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Ensure uv installs to the system path instead of a virtualenv
ENV UV_PROJECT_ENVIRONMENT=/usr/local

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# We use --frozen to ensure the lockfile is followed exactly
RUN uv sync --frozen --no-dev

# Copy the rest of the application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
