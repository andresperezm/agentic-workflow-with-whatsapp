FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Allow statements and log messages to immediately appear in the console
ENV PYTHONUNBUFFERED True

# Create a non-root user
RUN useradd -m appuser

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using public PyPI (ignoring local tainted lockfile)
RUN uv sync --no-cache

# Copy application code
COPY *.py ./

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Run the application
# uv run automatically uses the .venv created by uv sync
CMD ["uv", "run", "gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "0", "main:app"]