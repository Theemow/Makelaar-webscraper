# Updated Docker Scheduling Implementation Guide

I've updated your project configuration to handle all scheduling inside the Docker container. Here's what's been changed:

## 1. Crontab Configuration
The crontab file has been simplified to run the script inside the container at 12:00 and 19:00 every day.

## 2. Start Script Enhancements
The `start.sh` script now:
- Creates the logs directory if it doesn't exist
- Sets proper permissions for the crontab file
- Installs the crontab entry for the user inside the container
- Runs the database initialization and initial scraper run
- Starts cron in the foreground to keep the container running

## 3. Docker Setup Improvements
- The Docker volumes are now properly configured with read-only permissions where appropriate
- The Dockerfile separates crontab installation from crontab activation
- The crontab is now properly activated during container startup

## How to Deploy These Changes

### Step 1: Rebuild your Docker container
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Step 2: Verify that cron is running in the container
```bash
docker exec huurhuis-webscraper ps -ef
```
You should see a cron process running.

### Step 3: Check that the crontab is properly installed
```bash
docker exec huurhuis-webscraper crontab -l
```
This should show your scheduled jobs.

## Troubleshooting

If the container won't start properly:

1. Check the Docker logs:
```bash
docker logs huurhuis-webscraper
```

2. Make sure the start.sh file has the correct permissions:
```bash
chmod +x start.sh
```

3. Verify that cron is installed and working in the container:
```bash
docker exec huurhuis-webscraper which cron
```

## Notes on Scheduling

- The scraper will now run at:
  - 12:00 (noon) every day
  - 19:00 (7 PM) every day
- If you want to modify the schedule, edit the `crontab` file and rebuild the container
- All logs will be stored in the `logs` directory, which is mounted from your host

The internal container scheduling approach eliminates the need to set up cron jobs on your host system, making the application completely self-contained.
