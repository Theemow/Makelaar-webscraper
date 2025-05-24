"""
Base scraper module that defines the abstract base class for all website scrapers.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import requests

try:
    from bs4 import BeautifulSoup
except ImportError as exc:
    raise ImportError(
        "BeautifulSoup4 is required. Install it using 'pip install beautifulsoup4'"
    ) from exc

# Import the central logging service
from log_service import get_logger

# Get logger for this module
logger = get_logger("WebScraper")


class BaseScraper(ABC):
    """Abstract base class for web scraping real estate websites."""

    def __init__(self, base_url: str):
        """Initialize with the base URL of the real estate website.

        Args:
            base_url: The base URL of the real estate website.
        """
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Get a logger for the specific scraper instance
        self.logger = get_logger(self.__class__.__name__)

    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Retrieve the HTML content of a page.

        Args:
            url: The URL to retrieve.

        Returns:
            BeautifulSoup object with the HTML content, or None if an error occurs.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            self.logger.error("Error retrieving %s: %s", url, e)
            return None

    def clean_text(self, text: str) -> str:
        """Clean text by removing whitespace.

        Args:
            text: The text to clean.

        Returns:
            Cleaned text.
        """
        if text is None:
            return "N/A"
        return re.sub(r"\s+", " ", text).strip() or "N/A"

    def extract_rental_price(self, price_text: str) -> int:
        """Extract numeric rental price from text.

        Args:
            price_text: The text containing the rental price (e.g., "€ 1.250,- per maand")

        Returns:
            Integer representation of the rental price, or 0 if extraction fails.
        """
        if not price_text or price_text == "N/A":
            return 0

        try:
            # Remove all non-numeric characters except for decimals and thousands separators
            # Extract the first number sequence that could represent an amount
            matches = re.search(
                r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|\d+)", price_text
            )
            if not matches:
                self.logger.warning(
                    "Could not extract rental price from: %s", price_text
                )
                return 0  # Get the matched price
            price_str = matches.group(1)

            # Check if the price has a decimal part (after the last comma or dot)
            if "," in price_str or "." in price_str:
                # In Dutch format, commas are used as decimal separators
                # Replace dots as thousands separators first
                price_str = price_str.replace(".", "")

                # If there's a comma, it's likely a decimal separator
                if "," in price_str:
                    # Replace comma with dot (standard decimal in Python)
                    parts = price_str.split(",")
                    if (
                        len(parts) > 1 and len(parts[1]) <= 2
                    ):  # If it's cents (1 or 2 digits)
                        # Handle as decimal
                        price_str = parts[0] + "." + parts[1]
                    else:
                        # Treat as thousand separator
                        price_str = price_str.replace(",", "")

                # Convert to float first to handle decimals, then to int to get whole euros
                return int(float(price_str))
            else:
                # No decimal part, just remove any remaining non-numeric characters
                price_str = price_str.replace(".", "").replace(",", "")
                return int(price_str)
        except (ValueError, AttributeError) as e:
            self.logger.error(
                "Error extracting rental price from '%s': %s", price_text, e
            )
            return 0

    @abstractmethod
    def get_property_listings(self, page_num: int = 1) -> List[Dict[str, str]]:
        """Retrieve the properties of all rental properties from a page.

        Args:
            page_num: Page number to retrieve.

        Returns:
            List of dictionaries with rental property attributes.
        """
        # Abstract method doesn't need a pass statement

    @abstractmethod
    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """Retrieve detailed information about a specific rental property.

        Args:
            property_url: URL of the rental property.

        Returns:
            Dictionary with attributes of the rental property.
        """
        # Abstract method doesn't need a pass statement

    def get_all_listings(self, max_pages: int = 5) -> List[Dict[str, str]]:
        """Retrieve all rental properties up to a maximum number of pages.

        Args:
            max_pages: Maximum number of pages to retrieve.

        Returns:
            List of all found rental properties.
        """
        all_listings = []
        # Set to keep track of addresses we've already seen to prevent duplicates
        seen_addresses = set()

        for page in range(1, max_pages + 1):
            try:
                page_listings = self.get_property_listings(page)
                if not page_listings:
                    break

                # Check for duplicate listings by address
                unique_listings = []
                duplicate_count = 0

                for listing in page_listings:
                    address = listing.get("adres", "")
                    if address and address not in seen_addresses:
                        seen_addresses.add(address)
                        unique_listings.append(listing)
                    else:
                        duplicate_count += 1

                # If all listings on this page are duplicates, stop scraping
                if duplicate_count == len(page_listings):
                    break

                # Add only unique listings to our results
                all_listings.extend(unique_listings)

            except (requests.RequestException, ValueError, KeyError) as e:
                self.logger.error("Error processing page %d: %s", page, e)
                break

        return all_listings
