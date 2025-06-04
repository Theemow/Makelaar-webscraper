# Huurhuis Webscraper

A Python application that scrapes rental property listings from various Dutch real estate websites, stores them in a PostgreSQL database, and notifies you via email about new listings.

## Features

- Automatically scrapes rental property listings from multiple websites (currently supports 8 real estate websites):
  - Van Roomen Van de Bunt NVM Makelaars
  - Pararius
  - Zonnenberg Makelaardij
  - Ditters Makelaars
  - InterHouse Utrecht
  - InterHouse Amersfoort
  - VastgoedNederland Veenendaal
  - VBT Verhuurmakelaars
- Stores property data in a PostgreSQL database
- Detects new and removed property listings
- Sends email notifications with new rental properties
- Comprehensive logging system for monitoring and troubleshooting
- Supports multithreaded scraping for improved performance
- Easy deployment with Docker and automatic scheduling
- Support for JavaScript-heavy sites with Playwright or Selenium
- Easily extendable for additional real estate websites

## Prerequisites

### For Local Development

- Python 3.11 or higher
- PostgreSQL database server
- Required Python packages (all included in requirements.txt):
  - beautifulsoup4
  - requests
  - psycopg2-binary
  - typing-extensions
  - playwright
  - selenium
  - webdriver-manager
  - jupyter and notebook (for testing with the notebook)

### For Docker Deployment

- Docker and Docker Compose
- At least 2GB of free RAM
- Persistent storage for PostgreSQL data and logs

## Installation

### Standard Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/username/Makelaar-webscraper.git
   cd Makelaar-webscraper
   ```

2. Install required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install optional dependencies for JavaScript-heavy sites:

   ```bash
   playwright install --with-deps chromium
   # Selenium's webdriver-manager will download drivers on demand
   ```

### Docker Installation (Recommended)

The project includes Docker support for easy deployment:

1. Clone the repository and navigate to the project directory.

2. Create a `webscraper_config.py` file with your configuration (see Configuration section below).

3. Deploy with Docker Compose:

   ```bash
   docker-compose up -d
   ```

   This will:
   
   - Set up a PostgreSQL database container
   - Build and run the webscraper container
- Configure automatic scheduling via cron (runs hourly)
   - Store logs in a persistent volume

   To check logs:

   ```bash
   docker logs huurhuis-webscraper
   ```

## Configuration

Create a `webscraper_config.py` file in the root directory to manage all your credentials and settings:

```python
"""
Configuration file for HuurhuisWebscraper application.
This file contains sensitive information like email credentials.
Do not share or commit this file to version control.
"""

# Email configuration
EMAIL = {
    "sender_email": "your.email@gmail.com",  # Your Gmail address
    "sender_password": "your_app_password",  # Your Gmail App Password (not your regular password)
    "recipients": [
        "recipient1@example.com",
        "recipient2@example.com",
    ],  # List of email recipients
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
}

# Database configuration
DATABASE = {
    "dbname": "HuurhuizenWebscraper",  # Name of the database
    "user": "postgres",  # Database user
    "password": "admin",  # Database password
    "host": "postgres",  # For Docker: use service name / For local: use localhost
    "port": "5432",  # Database port (default is 5432 for PostgreSQL)
}
```

**Important Notes:**

- For Gmail, you need to use an App Password, not your regular password. You can generate an App Password in your Google Account security settings.
- The webscraper_config.py file contains sensitive information and is included in .gitignore by default to prevent it from being committed to version control.
- When using Docker, mount this file as a volume (see docker-compose.yml) or create a secure way to provide these credentials.

### Database Setup

#### Local Setup

If you're running the application locally (without Docker):

1. Install PostgreSQL if you haven't already
2. Create a new database called "HuurhuizenWebscraper"
3. Use the init_db.py script to create the necessary schema:

   ```bash
   python init_db.py
   ```

#### Docker Setup

When using Docker Compose, the database is automatically:

1. Created with the correct name
2. Initialized on first startup
3. Persisted through a Docker volume

The database schema is created using the `init_db.py` script, which creates the following structure:

```sql
CREATE TABLE broker_agencies (
    broker_id SERIAL PRIMARY KEY,
    broker_name TEXT NOT NULL,
    hyperlink TEXT NOT NULL
);

CREATE TABLE property (
    property_id SERIAL PRIMARY KEY,
    broker_id INT REFERENCES broker_agencies(broker_id),
    adres TEXT NOT NULL,
    hyperlink TEXT NOT NULL,
    toegevoegd_op DATE NOT NULL,
    naam_dorp_stad TEXT NOT NULL,
    price TEXT NOT NULL,
    size TEXT NOT NULL
);
```

Note: The database schema matches the structure in `data_access.py`. If you modify the data models, make sure to update the `init_db.py` schema accordingly.

## Usage

### Local Execution

You can run the application as a standalone Python script:

```bash
python huurhuis_webscraper.py
```

For testing individual scrapers or features, you can use the provided Jupyter Notebook:

```bash
jupyter notebook huurhuis_webscraper_tests.ipynb
```

### Docker Execution

When running with Docker Compose:

```bash
# Start the containers
docker-compose up -d

# View logs
docker logs huurhuis-webscraper

# Run the scraper manually (if needed)
docker exec huurhuis-webscraper python /app/huurhuis_webscraper.py
```

The application (whether run locally or in Docker) will:

1. Initialize the database and logger
2. Connect to each configured real estate website
3. Scrape property listings in parallel using multithreading
4. Compare newly scraped data with existing database records
5. Update the database with new and removed properties
6. Send email notifications if any new properties are found

When run in Docker, the application automatically executes hourly via cron.

## Docker Logging

The application is configured to work properly with Docker's logging system and tools like Portainer. Here's how to test and debug logging:

### Testing Docker Logging

To test if logging is working correctly in your Docker environment:

```bash
# Test logging functionality
docker exec huurhuis-webscraper python /app/test_docker_logging.py

# View real-time logs
docker logs -f huurhuis-webscraper

# View logs in Portainer
# Go to Containers -> huurhuis-webscraper -> Logs
```

### Troubleshooting Logging Issues

If logs are not appearing in Portainer or Docker logs:

1. **Check container status**:
   ```bash
   docker ps
   docker logs huurhuis-webscraper
   ```

2. **Verify cron is running**:
   ```bash
   docker exec huurhuis-webscraper ps aux | grep cron
   ```

3. **Test manual execution**:
   ```bash
   docker exec huurhuis-webscraper python -u /app/huurhuis_webscraper.py
   ```

4. **Check environment variables**:
   ```bash
   docker exec huurhuis-webscraper env | grep -E "(DOCKER_ENVIRONMENT|PYTHONUNBUFFERED)"
   ```

### Logging Configuration

The application uses several techniques to ensure proper Docker logging:

- **Unbuffered Output**: Python runs with `-u` flag and `PYTHONUNBUFFERED=1`
- **Direct stdout/stderr**: Logs are directed to `/proc/1/fd/1` and `/proc/1/fd/2`
- **Forced Flushing**: Log handlers force immediate flushing in Docker environment
- **Simple Formatting**: Docker-friendly log format without complex JSON structures

## How It Works

1. **Data Collection**: The application uses specialized scrapers for each real estate website to collect rental property listings.

2. **Data Processing**: The `connector` (Communication Layer) coordinates between scrapers and the database:
   - Compares newly scraped listings with existing database entries
   - Categorizes properties as new, existing, or removed
   - Updates the database accordingly

3. **Database Storage**: The `DataAccess` class handles all database operations:
   - Creating and updating property listings
   - Managing broker information
   - Tracking when properties are added or removed

4. **Notification**: If new properties are found, the application sends an email notification with details of the new listings.

5. **Logging**: The application uses a comprehensive logging system to track operations:
   - All actions are logged with timestamps
   - Logs are stored in the `logs/` directory with date and time in the filename
   - Different log levels (INFO, ERROR) help with troubleshooting

## Project Structure

### Core Files

- `huurhuis_webscraper.py`: Main Python script that ties everything together and contains execution code
- `huurhuis_webscraper_tests.ipynb`: Jupyter notebook for testing individual components
- `webscraper_config.py`: Configuration settings for email notifications and database connection
- `connector.py`: Main coordination module between scrapers and database
- `data_access.py`: Contains classes for database operations (DataAccess, BrokerAgency, Property)
- `mail_service.py`: Handles email notifications for new property listings
- `log_service.py`: Provides logging functionality throughout the application
- `init_db.py`: Script to initialize the database schema

### Docker Deployment Files

- `Dockerfile`: Defines the container image for the webscraper application
- `docker-compose.yml`: Orchestrates the deployment of both webscraper and PostgreSQL containers
- `crontab`: Defines the schedule for automatic execution in the container (runs hourly)
- `start.sh`: Container startup script that initializes the database and starts the cron service

### Scraper System

The project uses a modular scraper system where each website has its own specialized scraper that inherits from a base class:

- `scrapers/`: Directory containing scraper modules
  - `__init__.py`: Package initialization file
  - `base_scraper.py`: Abstract base class defining the scraper interface
  - `scraper_factory.py`: Factory for creating appropriate scrapers
  - `pararius_scraper.py`: Scraper for Pararius website
  - `vdbunt_scraper.py`: Scraper for Van Roomen Van de Bunt NVM Makelaars website
  - `zonnenberg_scraper.py`: Scraper for Zonnenberg Makelaardij website
  - `ditters_scraper.py`: Scraper for Ditters Makelaars website
  - `interhouse_scraper.py`: Scraper for InterHouse websites (Utrecht & Amersfoort)
  - `vastgoednederland_scraper.py`: Scraper for VastgoedNederland Veenendaal website
  - `vbt_scraper.py`: Scraper for VBT Verhuurmakelaars website

#### Supported Scrapers

| Scraper Type        | Website                         | Location Support    | JavaScript Required |
|---------------------|--------------------------------|---------------------|---------------------|
| vdbunt             | Van Roomen Van de Bunt         | Leusden area        | No                  |
| pararius           | Pararius                        | Various (Leusden, Veenendaal, Amersfoort, Ede) | No                  |
| zonnenberg         | Zonnenberg Makelaardij          | Veenendaal area     | No                  |
| ditters            | Ditters Makelaars               | Veenendaal area     | No                  |
| interhouse-utrecht  | InterHouse                     | Utrecht             | Yes (Selenium)      |
| interhouse-amersfoort| InterHouse                    | Amersfoort          | Yes (Selenium)      |
| vastgoednederland   | VastgoedNederland              | Veenendaal area     | No                  |
| vbt                | VBT Verhuurmakelaars            | Veenendaal area     | No                  |

## File Descriptions

### Main Files

- **huurhuis_webscraper.py**: This is the main Python script that orchestrates the entire system. It imports all necessary components and executes the main process to run all scrapers, update the database, and send email notifications.

- **huurhuis_webscraper_tests.ipynb**: Contains tests and examples for the different components of the system. Useful for debugging individual scrapers or testing new functionality.

- **webscraper_config.py**: Contains configuration variables for database connection and email sending. It's organized as two dictionaries: `DATABASE` for PostgreSQL connection parameters and `EMAIL` for SMTP settings.

- **connector.py**: Serves as the communication layer between scrapers and the database. It handles the logic for comparing new and existing listings, determining what's been added or removed, and coordinating updates.

- **data_access.py**: Provides all database-related functionality through the `DataAccess` class, including connection management and CRUD operations. It also contains the data models `BrokerAgency` and `Property`.

- **mail_service.py**: Handles the email notification system. It connects to the SMTP server defined in webscraper_config.py and formats/sends emails with information about new rental properties.

- **log_service.py**: Provides standardized logging functionality across the application, creating timestamped log files and offering different log levels.

- **init_db.py**: Script that handles database initialization, creating required tables if they don't exist, which is especially useful in Docker environments where the database starts fresh.

### Docker-Related Files

- **Dockerfile**: Defines how to build the Docker image for the application, including the Python environment, Chrome browser, and other dependencies.

- **docker-compose.yml**: Configures the multi-container setup with PostgreSQL and the webscraper service, defining how they interact, what volumes to mount, and environment variables.

- **crontab**: Contains the schedule for when the webscraper should run automatically (currently set to run hourly).

- **start.sh**: Shell script that runs when the Docker container starts, initializing the database, running an initial scrape, and starting the cron service.

### Supporting Files

- **scrapers/base_scraper.py**: Defines the `BaseScraper` abstract base class that all website-specific scrapers inherit from. It establishes the required interface methods that each scraper must implement.

- **scrapers/scraper_factory.py**: Uses the Factory pattern to create the appropriate scraper based on the website name. It centralizes scraper creation and makes it easy to add new scrapers.

## Extending the Project

### Adding New Scrapers

To add support for a new real estate website:

1. Create a new scraper class that inherits from `BaseScraper` in the scrapers directory
2. Implement the required methods for scraping properties from the website
3. Add the new scraper to the `ScraperFactory` in `scraper_factory.py`
4. Update the `makelaars` list in `run_scraper_proces()` function within `huurhuis_webscraper.py` to include the new website
5. Add a test method in the `huurhuis_webscraper_tests.ipynb` notebook to verify your new scraper works correctly

### Copilot template and example

Effective Prompt Template:

```text
Please implement a new scraper for [website name] at [website URL] that inherits from BaseScraper.

1. HTML Structure:
   - Here's a sample HTML snippet of a property listing from the website:
   [Paste 1-2 examples of HTML property listings]

2. Target Data:
   - Address information is located in: [CSS selector or HTML element]
   - Price information is located in: [CSS selector or HTML element]
   - Size/area information is located in: [CSS selector or HTML element]
   - Location/city information is located in: [CSS selector or HTML element]
   - Property URL/links use the format: [format or pattern]

3. Pagination:
   - The site uses [describe pagination method] for multiple pages
   - Pagination URLs follow this pattern: [pattern]

4. Integration Requirements:
   - Please add this scraper to the ScraperFactory and ensure it's properly integrated
   - Follow the same logging pattern as other scrapers
   - Use the BaseScraper as parent class
   - Add the new scraper to the makelaars array in the huurhuis_webscraper.py file
   - Create a scraper test method in the huurhuis_webscraper_tests.ipynb file following the same pattern as the other tests

5. Special Considerations:
   - Any specific challenges (e.g., dynamic content, anti-scraping measures)
   - Any unique data formatting needed for this site
```

Example:

```text
Please add a new scraper for ditters.nl with the URL https://www.ditters.nl/woningaanbod/?filter%5Bcategory%5D=%2FHuur

1. HTML Structure:
   - Here's a sample HTML snippet of a property listing from the website:
   [HTML snippet of a ditters.nl property listing]

2. Target Data:
   - Address: Found in h4.title element
   - City: Found in span.UITextArea element with "city" class
   - Price: Found in span.UILabelPrice element with "price" class
   - Size/area: Found in span.UITextArea element with "woonoppervlakte" class
   - Property links: They're based on href attributes in the parent div with class "template-row-link"

3. Pagination:
   - The site uses page numbers in URL parameters
   - Pagination URLs follow pattern: /woningaanbod/?page=[number]&filter[category]=/Huur

4. Integration Requirements:
   - Please add this scraper to the ScraperFactory
   - Implement logging similar to other scrapers
   - Follow the BaseScraper pattern
   - Add the new scraper to the makelaars array in the huurhuis_webscraper.py file
   - Create a scraper test method in the huurhuis_webscraper_tests.ipynb file following the same pattern as the other tests

5. Special Considerations:
   - Property addresses need to be extracted from multiple elements
   - Price format differs from other sites and needs normalization
```

### Customizing Database Schema

To modify the database schema:

1. Update the relevant classes in `data_access.py`
2. Modify the SQL queries in your database setup process
3. Update any related factory methods in the communication layer

### Scheduled Execution

The application is designed to run on a schedule to keep track of new rental listings.

#### Docker (Recommended)

The `docker-compose.yml` and `crontab` files are configured to run the scraper hourly. This is the recommended way to schedule the application.

#### Linux (Cron)

If running directly on a Linux system (without Docker), you can set up a cron job:

```bash
# Edit crontab
crontab -e

# Add this line to run hourly (at minute 0)
0 * * * * /usr/bin/python3 /path/to/Makelaar-webscraper/huurhuis_webscraper.py >> /path/to/logs/cron.log 2>&1
```

#### Windows

For Windows systems, use Task Scheduler:

1. Create a new task in Windows Task Scheduler
2. Set the trigger to run at specific times (e.g., hourly)
3. Set the action to start a program: `python` with arguments `C:\\path\\to\\Makelaar-webscraper\\huurhuis_webscraper.py`

Recommended scheduling: Hourly to catch new listings promptly

## License

This project is licensed under the MIT License - see the LICENSE file for details.