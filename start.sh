#!/bin/bash
set -e

# Set Docker environment variable for detection in code
export DOCKER_ENVIRONMENT=true

# Set proper permissions for crontab
chmod 0644 /etc/cron.d/huurhuis_crontab
crontab /etc/cron.d/huurhuis_crontab

# Initialize the database
echo "Initializing database..."
python /app/init_db.py

# Run the webscraper immediately for first run
echo "Starting initial webscraper run..."
python /app/huurhuis_webscraper.py

# Start cron in foreground (this keeps the container running)
echo "Starting cron service..."
echo "Webscraper will run daily at 12:00 and 18:00"
cron -f
