FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy CLI package and install
COPY pyproject.toml /tmp/pharabius/
COPY src/ /tmp/pharabius/src/
RUN pip install --no-cache-dir /tmp/pharabius/ && \
    rm -rf /tmp/pharabius/

# Copy platform package and install
COPY platform/backend/pyproject.toml /app/
COPY platform/backend/src/ /app/src/
RUN pip install --no-cache-dir .

# Create storage directory
RUN mkdir -p /var/lib/pharabius/bundles

EXPOSE 8000

CMD ["uvicorn", "pharabius_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
