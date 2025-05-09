# Huurhuis Webscraper

A Python application that scrapes rental property listings from various Dutch real estate websites, stores them in a PostgreSQL database, and notifies you via email about new listings.

## Features

- Automatically scrapes rental property listings from multiple websites (currently: VdBunt, Pararius, and Zonnenberg)
- Stores property data in a PostgreSQL database
- Detects new and removed property listings
- Sends email notifications with new rental properties
- Comprehensive logging system for monitoring and troubleshooting
- Easily extendable for additional real estate websites

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database server
- Required Python packages:
  - beautifulsoup4
  - requests
  - psycopg2
  - typing
  - dataclasses

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/Huurhuis-webscraper.git
   cd Huurhuis-webscraper
   ```

2. Install required dependencies:
   ```
   pip install beautifulsoup4 requests psycopg2
   ```

## Configuration

Create a `config.py` file in the root directory to manage all your credentials and settings:

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
    "recipients": ["recipient1@example.com", "recipient2@example.com"],  # List of email recipients
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587
}

# Database configuration
DATABASE = {
    "dbname": "HuurhuizenWebscraper",  # Name of the database
    "user": "postgres",  # Database user
    "password": "admin",  # Database password
    "host": "localhost",  # Database host (usually localhost)
    "port": "5432"  # Database port (default is 5432 for PostgreSQL)
}
```

**Important Notes:** 
- For Gmail, you need to use an App Password, not your regular password. You can generate an App Password in your Google Account security settings.
- The config.py file contains sensitive information and is included in .gitignore by default to prevent it from being committed to version control.

### Database Setup

The application uses PostgreSQL as its database system. Before running the application:

1. Install PostgreSQL if you haven't already
2. Create a new database called "HuurhuizenWebscraper"
3. Create the required tables by running the SQL queries below:

```sql
CREATE TABLE "BrokerAgencies" (
    "BrokerId" SERIAL PRIMARY KEY,
    "BrokerName" TEXT NOT NULL,
    "Hyperlink" TEXT NOT NULL
);

CREATE TABLE "Property" (
    "PropertyId" SERIAL PRIMARY KEY,
    "BrokerId" INT REFERENCES "BrokerAgencies"("BrokerId"),
    "Adres" TEXT NOT NULL,
    "Hyperlink" TEXT NOT NULL,
    "ToegevoegdOp" DATE NOT NULL,
    "NaamDorpStad" TEXT NOT NULL,
    "Price" TEXT NOT NULL,
    "Size" TEXT NOT NULL
);
```

## Usage

The easiest way to run the application is through the provided Jupyter Notebook:

1. Open the `HuurhuisWebscraper.ipynb` notebook:
   ```
   jupyter notebook HuurhuisWebscraper.ipynb
   ```

2. Run the notebook cells to execute the scraper and process the results.

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

- `HuurhuisWebscraper.ipynb`: Main Jupyter notebook that ties everything together and contains execution code
- `config.py`: Configuration settings for email notifications and database connection
- `connector.py`: Main coordination module between scrapers and database
- `data_access.py`: Contains classes for database operations (DataAccess, BrokerAgency, Property)
- `mail_service.py`: Handles email notifications for new property listings
- `log_service.py`: Provides logging functionality throughout the application

### Scraper System

- `scrapers/`: Directory containing scraper modules
  - `__init__.py`: Package initialization file
  - `base_scraper.py`: Abstract base class defining the scraper interface
  - `scraper_factory.py`: Factory for creating appropriate scrapers
  - `pararius_scraper.py`: Scraper for Pararius website
  - `vdbunt_scraper.py`: Scraper for VdBunt website
  - `zonnenberg_scraper.py`: Scraper for Zonnenberg Makelaardij website

## File Descriptions

### Main Files

- **HuurhuisWebscraper.ipynb**: This is the main notebook that orchestrates the entire system. It imports all necessary components and includes the main process to run all scrapers, update the database, and send email notifications.

- **Huurhuis_Webscraper_Tests.ipynb**: Contains tests and examples for the different components of the system.

- **config.py**: Contains configuration variables for database connection and email sending. It's organized as two dictionaries: `DATABASE` for PostgreSQL connection parameters and `EMAIL` for SMTP settings.

- **connector.py**: Serves as the communication layer between scrapers and the database. It handles the logic for comparing new and existing listings, determining what's been added or removed, and coordinating updates.

- **data_access.py**: Provides all database-related functionality through the `DataAccess` class, including connection management and CRUD operations. It also contains the data models `BrokerAgency` and `Property`.

- **mail_service.py**: Handles the email notification system. It connects to the SMTP server defined in config.py and formats/sends emails with information about new rental properties.

- **log_service.py**: Provides standardized logging functionality across the application, creating timestamped log files and offering different log levels.

### Supporting Files

- **scrapers/base_scraper.py**: Defines the `BaseScraper` abstract base class that all website-specific scrapers inherit from. It establishes the required interface methods that each scraper must implement.

- **scrapers/scraper_factory.py**: Uses the Factory pattern to create the appropriate scraper based on the website name. It centralizes scraper creation and makes it easy to add new scrapers.

## Extending the Project

### Adding New Scrapers

To add support for a new real estate website:

1. Create a new scraper class that inherits from `BaseScraper` in the scrapers directory
2. Implement the required methods for scraping properties from the website
3. Add the new scraper to the `ScraperFactory` in `scraper_factory.py`
4. Update the `makelaars` list in `run_scraper_proces()` function to include the new website

### Copilot template and example

Effective Prompt Template:

```txt
Please implement a new scraper for [website name] at [website URL].

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
   - add the new scraper to the makelaars array in the Huurhuis_webscraper file
   - Create a scraper test method in the Huurhuis_webscraper_tests file following the same pattern as the other tests

5. Special Considerations:
   - Any specific challenges (e.g., dynamic content, anti-scraping measures)
   - Any unique data formatting needed for this site
```

Example:

```txt
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
   - add the new scraper to the makelaars array in the Huurhuis_webscraper file
   - Create a scraper test method in the Huurhuis_webscraper_tests file following the same pattern as the other tests

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

The application can be scheduled to run automatically:

- On Linux/Unix: Use crontab to schedule the execution at specified intervals
- On Windows: Use Task Scheduler to run the script at specified times
- Recommended scheduling: Twice daily (around 12:00 and 18:00) to catch new listings

## License

This project is licensed under the MIT License - see the LICENSE file for details.