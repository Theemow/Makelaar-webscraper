"""
Pararius scraper module that implements the scraping of Pararius real estate website.
"""

import logging
import re  # Added for regex support
from typing import Dict, List
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger("WebScraper")


class ParariusScraper(BaseScraper):
    """Scraper for the Pararius website."""

    def __init__(self):
        """Initialize the Pararius scraper."""
        super().__init__("https://www.pararius.nl")

    def clean_city_name(self, text):
        """Remove postal code from city name and clean the text."""
        # First apply the regular clean_text method
        text = self.clean_text(text)

        # Remove postal code pattern (e.g. '3512 AG ' or '1234 AB ')
        clean_text = re.sub(r"\d{4}\s*[A-Z]{2}\s*", "", text)

        # Extract just the city name (before any parentheses)
        city_match = re.match(r"([^(]+)", clean_text)
        if city_match:
            return city_match.group(1).strip()

        return clean_text

    def clean_price_text(self, text):
        """Clean rental price text by removing the 'Transparant' information block.

        Args:
            text: The price text to clean.

        Returns:
            Cleaned price text.
        """
        # First apply the regular clean_text method
        text = self.clean_text(text)

        # Remove the "Transparant Meer informatie..." text block
        transparant_pattern = r"Transparant Meer informatie.*?Meer informatie Sluiten"
        clean_text = re.sub(transparant_pattern, "", text, flags=re.DOTALL)

        # Make sure we have a clean rental price
        return clean_text.strip() or "N/A"

    def get_property_listings(self, page_num: int = 1) -> List[Dict[str, str]]:
        """Retrieve all properties from a Pararius page.

        Args:
            page_num: Page number to retrieve.

        Returns:
            List of dictionaries with property attributes.
        """
        # Fix URL construction with proper path separator
        if page_num == 1:
            url = f"{self.base_url}/huurwoningen/leusden/"
        else:
            url = f"{self.base_url}/huurwoningen/leusden/page-{page_num}"

        soup = self.get_page_content(url)
        if not soup:
            return []

        properties = []

        # The main container that holds all property listings
        listings = soup.select("ul.search-list li.search-list__item--listing")

        if not listings:
            # Try with new website structure
            listings = soup.select("section.listing-search-item")

        if not listings:
            return []

        for listing in listings:
            try:  # Initialize property data
                property_data = {
                    "adres": "N/A",
                    "naam_dorp_stad": "N/A",
                    "huurprijs": 0,
                    "oppervlakte": "N/A",
                    "link": "N/A",
                }

                # Extract address
                address_elem = listing.select_one(".listing-search-item__link--title")
                if address_elem:
                    property_data["adres"] = self.clean_text(address_elem.text)

                # Extract city/town name
                city_elem = listing.select_one(".listing-search-item__sub-title")
                if city_elem:
                    property_data["naam_dorp_stad"] = self.clean_city_name(
                        city_elem.text
                    )  # Extract price
                price_elem = listing.select_one(".listing-search-item__price")
                if price_elem:
                    price_text = self.clean_price_text(price_elem.text)
                    # Store the numeric price directly
                    property_data["huurprijs"] = self.extract_rental_price(price_text)

                # Extract area - try both old and new format
                area_elem = listing.select_one(
                    ".listing-search-item__features .surface"
                )
                if not area_elem:
                    area_elem = listing.select_one(
                        ".illustrated-features__item--surface-area"
                    )

                if area_elem:
                    property_data["oppervlakte"] = self.clean_text(area_elem.text)

                # Extract link
                link_elem = listing.select_one(".listing-search-item__link--title")
                if link_elem and link_elem.get("href"):
                    property_data["link"] = urljoin(
                        "https://www.pararius.nl", link_elem.get("href")
                    )

                properties.append(property_data)

            except (ValueError, AttributeError, IndexError, TypeError) as e:
                logger.error("Error processing property: %s", e)

        return properties

    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """Retrieve detailed information about a specific property.

        Args:
            property_url: URL of the property.

        Returns:
            Dictionary with property attributes.
        """
        soup = self.get_page_content(property_url)
        details = {
            "adres": "N/A",
            "naam_dorp_stad": "N/A",
            "huurprijs": "N/A",
            "oppervlakte": "N/A",
            "link": property_url,
        }

        try:
            # Extract address
            address_elem = soup.select_one("h1.listing-detail-summary__title")
            if address_elem:
                details["adres"] = self.clean_text(address_elem.text)

            # Extract city/location
            location_elem = soup.select_one("div.listing-detail-summary__location")
            if location_elem:
                details["naam_dorp_stad"] = self.clean_city_name(
                    location_elem.text
                )  # Extract price
            price_elem = soup.select_one("span.listing-detail-summary__price")
            if price_elem:
                price_text = self.clean_text(price_elem.text)
                details["huurprijs"] = self.extract_rental_price(price_text)

            # Extract surface area
            features = soup.select("ul.listing-features li")
            for feature in features:
                if "Woonoppervlakte" in feature.text:
                    details["oppervlakte"] = self.clean_text(
                        feature.text.replace("Woonoppervlakte", "")
                    )
                    break

        except (ValueError, AttributeError, TypeError) as e:
            logger.error("Error retrieving details from %s: %s", property_url, e)

        return details
