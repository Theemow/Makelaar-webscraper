#!/bin/bash
set -e

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
