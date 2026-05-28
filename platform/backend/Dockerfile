FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# Copy source
COPY src/ src/

# Install package
RUN pip install --no-cache-dir -e .

# Create storage directory
RUN mkdir -p /var/lib/pharabius/bundles

EXPOSE 8000

CMD ["uvicorn", "pharabius_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
