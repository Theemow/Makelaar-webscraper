# filepath: c:\Users\User\Documents\GitHub\Makelaar-webscraper\scrapers\vbt_scraper.py
"""
VBT Verhuurmakelaars scraper for the HuurhuisWebscraper.

This module contains the scraper for VBT Verhuurmakelaars (https://vbtverhuurmakelaars.nl/).
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from log_service import get_logger
from scrapers.base_scraper import BaseScraper


class VBTScraper(BaseScraper):
    """
    Scraper for VBT Verhuurmakelaars website.

    This scraper handles the extraction of rental properties from
    https://vbtverhuurmakelaars.nl/woningen
    """

    def __init__(self, base_url="https://vbtverhuurmakelaars.nl/woningen"):
        """
        Initialize the VBT scraper.

        Args:
            base_url: The base URL for VBT Verhuurmakelaars listings
        """
        # Call parent constructor to initialize base attributes including logger
        super().__init__(base_url)

        # Filter cookie required to access the site with region settings
        self.cookies = {
            "language": "nl",
            "cookie-consent": '{"functional":true,"analytics":true,"marketing":true}',
            "filter_properties": '{"city":"Veenendaal","radius":15,"address":"","priceRental":{"min":0,"max":0},"availablefrom":"","surface":"","rooms":0,"typeCategory":""}',
        }

    def get_property_listings(self, page_num=1) -> List[Dict[str, str]]:
        """
        Get property listings from VBT Verhuurmakelaars.

        Args:
            page_num: Page number to scrape (default: 1)

        Returns:
            List of property dictionaries with extracted information
        """
        page_url = self.base_url
        if page_num > 1:
            page_url = f"{self.base_url}/{page_num}"

        try:
            response = requests.get(
                page_url, headers=self.headers, cookies=self.cookies, timeout=15
            )
            response.raise_for_status()  # Raise error for bad responses
            soup = BeautifulSoup(response.text, "html.parser")
            properties = []

            # Find all property listings
            property_items = soup.select("a.property")

            for item in property_items:
                try:
                    property_data = {}

                    # Extract the relative URL and convert to absolute
                    property_url = item.get("href")
                    if property_url:
                        property_data["link"] = urljoin(
                            "https://vbtverhuurmakelaars.nl", property_url
                        )

                    # Extract city (location)
                    city_element = item.select_one("div.items > div:first-child")
                    if city_element:
                        property_data["naam_dorp_stad"] = self.clean_text(
                            city_element.text
                        )

                    # Extract address
                    address_element = item.select_one("span.normal")
                    if address_element:
                        property_data["adres"] = self.clean_text(address_element.text)

                    # Extract price
                    price_element = item.select_one("div.price")
                    if price_element:
                        price = self.clean_text(price_element.text)
                        # Ensure proper € symbol and formatting
                        if "€" not in price:
                            price = re.sub(r"^(\d)", "€ \\1", price)
                        property_data["huurprijs"] = price

                    # Extract size/area
                    size_row = item.select("table tr")
                    for row in size_row:
                        header = row.select_one("td:first-child")
                        if header and "Woonoppervlakte" in header.text:
                            value = row.select_one("td:nth-child(2)")
                            if value:
                                size = self.clean_text(value.text)
                                # Ensure proper m² symbol
                                if "m²" not in size:
                                    size = size.replace("m2", "m²")
                                    # If no unit at all, add m²
                                    if not re.search(r"m[²2]", size):
                                        size = f"{size} m²"
                                property_data["oppervlakte"] = size
                                break

                    # Fill in N/A for any missing properties
                    for key in [
                        "adres",
                        "naam_dorp_stad",
                        "huurprijs",
                        "oppervlakte",
                        "link",
                    ]:
                        if key not in property_data:
                            property_data[key] = "N/A"
                            self.logger.warning(f"Missing {key} for property")

                    properties.append(property_data)
                except Exception as e:
                    self.logger.error(f"Error extracting property data: {e}")
                    continue

            return properties

        except Exception as e:
            self.logger.error(f"Error scraping VBT page {page_num}: {e}")
            return []

    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """
        Get detailed information for a single property.

        Args:
            property_url: URL of the property detail page

        Returns:
            Dictionary with property details
        """
        details = {}

        try:
            response = requests.get(
                property_url, headers=self.headers, cookies=self.cookies, timeout=15
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract basic information already available
            title_element = soup.select_one("h1")
            if title_element:
                details["title"] = self.clean_text(title_element.text)

            # Extract additional details as available
            detail_rows = soup.select("div.specs table tr")
            for row in detail_rows:
                header = row.select_one("th")
                value = row.select_one("td")
                if header and value:
                    key = self.clean_text(header.text).lower().replace(" ", "_")
                    details[key] = self.clean_text(value.text)

            return details

        except Exception as e:
            self.logger.error(f"Error fetching property details: {e}")
            return details

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Replace &nbsp; with space
        text = text.replace("\xa0", " ")
        text = text.replace("mÂ²", "")

        # Correct special characters
        text = text.replace("€&nbsp;", "€ ")
        text = text.replace("â¬Â", "€")
        text = text.replace("m&sup2;", "m²")
        text = text.replace("m2", "m²")

        # Remove multiple spaces, newlines, tabs
        text = re.sub(r"\s+", " ", text)

        # Strip leading/trailing whitespace
        return text.strip()
