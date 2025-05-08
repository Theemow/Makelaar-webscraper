"""
Ditters scraper module for scraping rental properties from the Ditters website.
"""

import logging
import re
from typing import Dict, List
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper

try:
    from bs4 import BeautifulSoup
except ImportError as exc:
    raise ImportError(
        "BeautifulSoup4 is required. Install it using 'pip install beautifulsoup4'"
    ) from exc

# Get logger for this module
logger = logging.getLogger("WebScraper")


class DittersScraper(BaseScraper):
    """Scraper specifically for the Ditters website."""

    def __init__(self):
        """Initialize the Ditters scraper."""
        super().__init__("https://www.ditters.nl")
        # Add extended headers to mimic a real browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "nl,en-US;q=0.7,en;q=0.3",
        }

    def get_property_listings(self, page_num: int = 1) -> List[Dict[str, str]]:
        """Retrieve rental properties from the Ditters website.

        Args:
            page_num: Page number to retrieve

        Returns:
            List of dictionaries with rental property attributes.
        """
        # Construct URL with pagination if needed
        if page_num > 1:
            url = f"{self.base_url}/woningaanbod/?filter%5Bcategory%5D=%2FHuur&page={page_num}"
        else:
            url = f"{self.base_url}/woningaanbod/?filter%5Bcategory%5D=%2FHuur"

        soup = self.get_page_content(url)
        if not soup:
            logger.error("Failed to get content from %s", url)
            return []

        listings = []

        # Look for property items
        property_items = soup.select(
            "div.aanbod-list__inner.product-starters-template-row-link"
        )

        if not property_items:
            # Try alternative selector patterns if the primary one doesn't work
            property_items = soup.select('div[class*="template-row-link"]')

        logger.info(
            "Found %d properties on Ditters website (page %d)",
            len(property_items),
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

                # Get the link to the property
                # First try to get href from the parent element
                property_url = item.get("href")

                # If not found, try to find it in a nested element
                if not property_url:
                    link_element = item.find("a")
                    if link_element:
                        property_url = link_element.get("href")

                # If still no URL, the page might use JavaScript for navigation
                # Try to construct the URL based on the available data
                if not property_url:
                    # Look for any data that might help construct the URL
                    address_element = item.select_one("h4.title")
                    city_element = item.select_one("span.city")

                    if address_element and city_element:
                        address_text = self.clean_text(address_element.text)
                        city_text = self.clean_text(city_element.text)

                        # Construct URL from city and address
                        slug = f"{city_text.lower()}-{address_text.lower().replace(' ', '-')}"
                        property_url = f"{self.base_url}/woningaanbod/{slug}/"

                # Make sure the URL is absolute
                if property_url and not property_url.startswith("http"):
                    property_url = urljoin(self.base_url, property_url)

                property_data["link"] = property_url if property_url else "N/A"

                # Extract address
                address_element = item.select_one("h4.title")
                if address_element:
                    property_data["adres"] = self.clean_text(address_element.text)

                # Extract location/city
                city_element = item.select_one("div.UITextArea.element-content span")
                if city_element:
                    property_data["naam_dorp_stad"] = self.clean_text(city_element.text)

                # Extract price
                price_element = item.select_one("div.UILabelPrice.element-content span")
                if price_element:
                    property_data["huurprijs"] = self.clean_text(price_element.text)

                # Find all size/area related elements
                area_elements = item.select("div.metadata-item span")
                for element in area_elements:
                    text = self.clean_text(element.text)
                    if "m²" in text or "m2" in text:
                        property_data["oppervlakte"] = text
                        break

                # Only add to the list if we have at minimum an address and a link
                if property_data["adres"] != "N/A" and property_data["link"] != "N/A":
                    listings.append(property_data)

            except (AttributeError, TypeError, KeyError) as e:
                logger.error("Error processing property: %s", e)
                continue

        return listings

    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """Retrieve detailed information about a specific rental property from Ditters website.

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
            address_element = soup.select_one("h1.title, h1.property-title, h3.title")
            if address_element:
                details["adres"] = self.clean_text(address_element.text)

            # Extract city/location
            city_element = soup.select_one("span.city, div.city span")
            if city_element:
                details["naam_dorp_stad"] = self.clean_text(city_element.text)

            # Extract price
            price_element = soup.select_one(
                "span.price, div.price span, div.UILabelPrice span"
            )
            if price_element:
                details["huurprijs"] = self.clean_text(price_element.text)

            # Extract area - look for elements containing m²
            for element in soup.select(
                "div.metadata-item span, div.specifications div, div.kenmerk"
            ):
                text = self.clean_text(element.text)
                if "m²" in text or "m2" in text:
                    # Check if it's specifically about living area
                    if (
                        "woonoppervlakte" in text.lower()
                        or "oppervlakte" in text.lower()
                    ):
                        area_match = re.search(r"(\d+)\s*(?:m²|m2)", text)
                        if area_match:
                            details["oppervlakte"] = f"{area_match.group(1)}m²"
                            break

            # If we still don't have an area, take the first element that contains m²
            if details["oppervlakte"] == "N/A":
                for element in soup.select("span, div"):
                    text = self.clean_text(element.text)
                    if "m²" in text or "m2" in text:
                        area_match = re.search(r"(\d+)\s*(?:m²|m2)", text)
                        if area_match:
                            details["oppervlakte"] = f"{area_match.group(1)}m²"
                            break

        except (AttributeError, TypeError) as e:
            logger.error("Error retrieving details from %s: %s", property_url, e)

        return details
