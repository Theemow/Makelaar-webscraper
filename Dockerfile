FROM python:3.11-slim

# Metadata
LABEL maintainer="Maintainer <timo.kamermans@gmail.com>"
LABEL description="HuurhuisWebscraper - Een webapp die huurhuizen verzamelt van verschillende makelaarsites"
LABEL version="1.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Amsterdam

# Install PostgreSQL client tools, cron, Chrome dependencies and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    libpq-dev \
    cron \
    wget \
    gnupg \
    unzip \
    # Chrome dependencies
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libxss1 \
    libasound2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
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

# Ensure Selenium and webdriver-manager are correctly installed
RUN pip install --no-cache-dir selenium webdriver-manager \
    && echo "export PATH=/usr/local/bin:$PATH" >> /etc/profile

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Install crontab
COPY crontab /etc/cron.d/huurhuis_crontab
RUN chmod 0644 /etc/cron.d/huurhuis_crontab && \
    crontab /etc/cron.d/huurhuis_crontab

# Create a startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Command to run the application with cron
CMD ["/app/start.sh"]
