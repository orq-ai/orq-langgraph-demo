FROM python:3.12.3-slim

WORKDIR /app

# Environment variables for uv
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
ENV UV_COMPILE_BYTECODE=1

# Install system dependencies including make, sqlite3, and unzip
RUN apt-get update && apt-get install -y \
    vim \
    make \
    sqlite3 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies
RUN uv sync --frozen

# Copy source code
COPY .chainlit/ .chainlit/
COPY src/ ./src/
COPY data/ ./data/
COPY docs/ ./docs/
COPY scripts/ ./scripts/
COPY resources/ ./resources/
COPY public/ ./public/

# Copy PDF files to public directory for web access
RUN cp docs/*.pdf public/ 2>/dev/null || true

COPY chainlit.md ./
COPY Makefile ./

# Expose Chainlit default port
EXPOSE 8000

# Set environment variable for Chainlit
ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=8000

# Simple setup for sqlite because is small enough to fit in the container
RUN make setup-structured-db

# Run the Chainlit application
CMD ["uv", "run", "chainlit", "run", "src/chainlit_app.py", "--host", "0.0.0.0", "--port", "8000"]
