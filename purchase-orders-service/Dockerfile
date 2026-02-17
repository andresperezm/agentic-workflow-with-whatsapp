FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Allow statements and log messages to immediately appear in the console
ENV PYTHONUNBUFFERED True

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
# We remove --frozen to allow resolving dependencies from public PyPI
# instead of relying on the lockfile generated in a custom environment.
RUN uv sync --no-cache

# Copy application code
COPY main.py .

# Environment variables
ENV PORT=8080
EXPOSE 8080

# Run the application
# uv run automatically uses the .venv created by uv sync
CMD ["uv", "run", "main.py"]
