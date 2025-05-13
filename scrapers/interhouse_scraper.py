"""
InterHouse scraper module for scraping rental properties from the Interhouse website.
This scraper uses Selenium to render JavaScript-based content.
"""

import re
import time
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin, parse_qs, urlparse

from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper

# Conditional import of Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Import the central logging service
from log_service import get_logger

# Get logger for this module
logger = get_logger("WebScraper")


class InterHouseScraper(BaseScraper):
    """Scraper specifically for the InterHouse website which uses JavaScript for content loading."""

    # Define supported locations
    LOCATIONS = {"Utrecht": "Utrecht_Algemeen", "Amersfoort": "Amersfoort_Algemeen"}

    def __init__(self, location: str = "Utrecht"):
        """Initialize the InterHouse scraper.

        Args:
            location: The location to scrape, either "Utrecht" or "Amersfoort"
        """
        super().__init__("https://interhouse.nl")
        self.driver = None

        # Set the location (default to Utrecht if invalid location provided)
        if location in self.LOCATIONS:
            self.location = location
            self.location_id = self.LOCATIONS[location]
        else:
            self.location = "Utrecht"
            self.location_id = self.LOCATIONS["Utrecht"]
            logger.warning(
                f"Invalid location '{location}'. Using default location '{self.location}'"
            )

        # Check if Selenium is available
        if not SELENIUM_AVAILABLE:
            logger.warning(
                "Selenium is not installed. JavaScript rendering will not be available. "
                "Please install it with: pip install selenium webdriver-manager"
            )

    def _setup_driver(self):
        """Set up the Selenium WebDriver if it's not already initialized."""
        if self.driver is not None:
            return

        if SELENIUM_AVAILABLE:
            try:
                # Set up Chrome options for headless browsing
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument(f"user-agent={self.headers['User-Agent']}")

                # Try to use webdriver-manager for Chrome driver installation
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    from selenium.webdriver.chrome.service import Service

                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                except ImportError:
                    # Fall back to direct Chrome driver instantiation
                    self.driver = webdriver.Chrome(options=options)

                self.logger.info("Selenium WebDriver initialized successfully")
            except Exception as e:
                self.logger.error(f"Error initializing Selenium WebDriver: {e}")
                self.driver = None
        else:
            self.logger.warning("Selenium is not available")

    def _quit_driver(self):
        """Quit the Selenium WebDriver if it's initialized."""
        if self.driver is not None:
            try:
                self.driver.quit()
                self.driver = None
            except Exception as e:
                self.logger.error(f"Error quitting WebDriver: {e}")

    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Override the get_page_content method to use Selenium for JavaScript rendering.

        Args:
            url: The URL to retrieve.

        Returns:
            BeautifulSoup object with the rendered HTML content, or None if an error occurs.
        """
        self.logger.info("Retrieving page with Selenium: %s", url)

        # If Selenium is not available, fall back to the base method
        if not SELENIUM_AVAILABLE:
            self.logger.warning(
                "Falling back to requests as Selenium is not installed. "
                "This may result in incomplete data."
            )
            return super().get_page_content(url)

        try:
            # Set up the driver if needed
            self._setup_driver()

            # If driver setup failed, fall back to the base method
            if self.driver is None:
                self.logger.warning(
                    "WebDriver setup failed. Falling back to requests method."
                )
                return super().get_page_content(url)

            # Navigate to the URL
            self.driver.get(url)

            # Wait for the page to load (wait for some expected element)
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: (
                        driver.find_elements(By.CSS_SELECTOR, "div.c-result-item")
                        or EC.text_to_be_present_in_element(
                            (By.ID, "building-search-results"),
                            "Er zijn helaas geen resultaten gevonden",
                        )(driver)
                    )
                )
            except Exception as e:
                self.logger.warning(f"Timeout waiting for page elements: {e}")
                # Continue anyway as the page might still have loaded partially

            # Get the page content
            content = self.driver.page_source

            return BeautifulSoup(content, "html.parser")
        except Exception as e:
            self.logger.error("Error retrieving %s with Selenium: %s", url, e)
            # As a fallback, try the regular requests method
            self.logger.info("Falling back to regular requests method")
            return super().get_page_content(url)

    def get_property_listings(self, page_num: int = 1) -> List[Dict[str, str]]:
        """Retrieve rental properties from the InterHouse website.

        Args:
            page_num: Page number to retrieve

        Returns:
            List of dictionaries with rental property attributes.
        """
        # Construct URL with pagination
        base_search_url = f"{self.base_url}/huurwoningen/"
        params = f"?location_id={self.location_id}&number_of_results=20&sort=date-desc&display=list"

        if page_num > 1:
            url = f"{base_search_url}{params}&paging={page_num}"
        else:
            url = f"{base_search_url}{params}"

        soup = self.get_page_content(url)
        if not soup:
            self.logger.error("Failed to get content from %s", url)
            return []

        listings = []

        # Find all property items
        property_items = soup.select("div.c-result-item.building-result")

        self.logger.info(
            "Found %d properties on InterHouse website for %s (page %d)",
            len(property_items),
            self.location,
            page_num,
        )

        for item in property_items:
            try:
                # Initialize property data with default values
                property_data = {
                    "adres": "N/A",
                    "link": "N/A",
                    "naam_dorp_stad": "N/A",
                    "huurprijs": "N/A",
                    "oppervlakte": "N/A",
                }

                # Extract address
                address_element = item.select_one("span.c-result-item__title-address")
                if address_element:
                    property_data["adres"] = self.clean_text(address_element.text)

                # Extract city/location
                city_element = item.select_one("p.c-result-item__location-label")
                if city_element:
                    property_data["naam_dorp_stad"] = self.clean_text(city_element.text)

                # Extract price
                price_element = item.select_one("p.c-result-item__price-label")
                if price_element:
                    property_data["huurprijs"] = self.clean_text(price_element.text)

                # Extract area/size
                # Find the element that contains "Woonoppervlakte"
                for table_item in item.select("div.c-result-item__data-table-item"):
                    header = table_item.select_one("p.c-result-item__data-header")
                    if header and "Woonoppervlakte" in header.text:
                        area_value = table_item.select_one(
                            "p.c-result-item__data-value"
                        )
                        if area_value:
                            # Clean and extract the area, preserving the m² format
                            area_text = area_value.get_text(strip=True)
                            # Replace <sup>2</sup> with ²
                            area_text = re.sub(r"m</?sup>2</sup>", "m²", area_text)
                            property_data["oppervlakte"] = self.clean_text(area_text)
                            break

                # Extract link
                link_element = item.select_one("div.c-result-item__button-wrapper a")
                if not link_element:
                    # Try alternative selector for links
                    link_element = item.select_one("a.c-button")

                if link_element and link_element.get("href"):
                    property_data["link"] = urljoin(
                        self.base_url, link_element.get("href")
                    )
                else:
                    # Try to find any link in the item that might point to the property
                    any_link = item.select_one("a")
                    if any_link and any_link.get("href"):
                        property_data["link"] = urljoin(
                            self.base_url, any_link.get("href")
                        )

                # Only add properties that have at least an address and location
                if (
                    property_data["adres"] != "N/A"
                    and property_data["naam_dorp_stad"] != "N/A"
                ):
                    listings.append(property_data)

            except (AttributeError, TypeError, ValueError) as e:
                self.logger.error("Error processing property: %s", e)
                continue

        return listings

    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """Retrieve detailed information about a specific rental property from the InterHouse website.

        Args:
            property_url: URL of the rental property.

        Returns:
            Dictionary with attributes of the rental property.
        """
        soup = self.get_page_content(property_url)
        if not soup:
            return {
                "adres": "N/A",
                "link": property_url,
                "naam_dorp_stad": "N/A",
                "huurprijs": "N/A",
                "oppervlakte": "N/A",
            }

        details = {
            "adres": "N/A",
            "link": property_url,
            "naam_dorp_stad": "N/A",
            "huurprijs": "N/A",
            "oppervlakte": "N/A",
        }

        try:
            # Extract address from detail page
            address_element = soup.select_one("h1.c-listing-heading__address-part")
            if address_element:
                details["adres"] = self.clean_text(address_element.text)

            # Extract city/location
            city_element = soup.select_one("p.c-listing-heading__location-label")
            if city_element:
                details["naam_dorp_stad"] = self.clean_text(city_element.text)

            # Extract price
            price_element = soup.select_one("p.c-listing-heading__price-label")
            if price_element:
                details["huurprijs"] = self.clean_text(price_element.text)

            # Extract area/size
            # Look for the specifications table that contains the area information
            specs_items = soup.select("div.c-listing-specs div.c-listing-specs__item")
            for spec in specs_items:
                label_elem = spec.select_one("p.c-listing-specs__label")
                value_elem = spec.select_one("p.c-listing-specs__value")

                if label_elem and "Woonoppervlakte" in label_elem.text and value_elem:
                    # Clean and extract the area, preserving the m² format
                    area_text = value_elem.get_text(strip=True)
                    # Replace <sup>2</sup> with ²
                    area_text = re.sub(r"m</?sup>2</sup>", "m²", area_text)
                    details["oppervlakte"] = self.clean_text(area_text)
                    break

            # If we couldn't find the area in the specifications table,
            # try looking elsewhere on the page
            if details["oppervlakte"] == "N/A":
                for element in soup.select("p, div, span"):
                    text = element.get_text(strip=True)
                    if "m²" in text or "m2" in text:
                        area_match = re.search(r"(\d+)\s*(?:m²|m2)", text)
                        if area_match:
                            details["oppervlakte"] = f"{area_match.group(1)}m²"
                            break

        except (AttributeError, TypeError) as e:
            self.logger.error("Error retrieving details from %s: %s", property_url, e)

        return details

    def get_all_listings(self, max_pages: int = 5) -> List[Dict[str, str]]:
        """Override get_all_listings to ensure proper handling with Selenium.

        Args:
            max_pages: Maximum number of pages to retrieve.

        Returns:
            List of all found rental properties.
        """
        # First check if Selenium is available and warn if it's not
        if not SELENIUM_AVAILABLE:
            self.logger.warning(
                "Selenium is not installed. This may result in incomplete data. "
                "Please install with: pip install selenium webdriver-manager"
            )

        try:
            # Use the base class implementation
            listings = super().get_all_listings(max_pages=max_pages)

            # Close the driver when done
            self._quit_driver()

            return listings
        except Exception as e:
            self.logger.error(f"Error in get_all_listings: {e}")
            # Make sure to close the driver even if there's an error
            self._quit_driver()
            return []
