FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ .

# Copy database migrations and seed (from repo root)
COPY db/migrations /app/migrations
COPY db/seed /app/seed

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Run migrations and start the application
ENTRYPOINT ["/app/entrypoint.sh"]