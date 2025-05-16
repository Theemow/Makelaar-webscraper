FROM python:3.11-slim

# Metadata
LABEL maintainer="Maintainer <timo.kamermans@gmail.com>"
LABEL description="HuurhuisWebscraper - Een webapp die huurhuizen verzamelt van verschillende makelaarsites"
LABEL version="1.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Amsterdam

# Install PostgreSQL client tools and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Working directory in container
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# For JavaScript-heavy sites (optional)
RUN pip install --no-cache-dir playwright \
    && playwright install --with-deps chromium

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Command to run the application
CMD python init_db.py && python huurhuis_webscraper.py
