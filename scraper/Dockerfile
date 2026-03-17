FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from scraper (shared dependencies)
COPY scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scraper code
COPY scraper/ ./scraper/

# Copy API code (needed for shared database models)
COPY api/ ./api/

# Set working directory to scraper
WORKDIR /app/scraper

# Default command - runs the APScheduler to manage all scrapers
CMD ["python", "scheduler.py"]
