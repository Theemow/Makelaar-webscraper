"""
Nederwoon scraper module for scraping rental properties from the Nederwoon website.
Supports multiple locations including Amersfoort and Utrecht.
"""

import re
from typing import Dict, List
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper

# Get logger for this module
from log_service import get_logger

logger = get_logger("WebScraper")


class NederwoonScraper(BaseScraper):
    """Scraper specifically for the Nederwoon website."""

    # Define supported locations
    LOCATIONS = {"Amersfoort": "Amersfoort", "Utrecht": "Utrecht"}

    def __init__(self, location: str = "Amersfoort"):
        """Initialize the Nederwoon scraper.

        Args:
            location: The location to scrape, either "Amersfoort" or "Utrecht"
        """
        super().__init__("https://www.nederwoon.nl")

        # Set the location (default to Amersfoort if invalid location provided)
        if location in self.LOCATIONS:
            self.location = location
        else:
            self.logger.warning(
                "Invalid location '%s', defaulting to Amersfoort", location
            )
            self.location = "Amersfoort"
        # Add extended headers to mimic a real browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "nl,en-US;q=0.7,en;q=0.3",
            # Removed Accept-Encoding to avoid Brotli compression issues
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def get_property_listings(self, page_num: int = 1) -> List[Dict[str, str]]:
        """Retrieve rental properties from the Nederwoon website.

        Args:
            page_num: Page number to retrieve (ignored for Nederwoon as they don't support pagination).

        Returns:
            List of dictionaries with rental property attributes.
        """
        # Nederwoon doesn't support pagination, so we only fetch the first page
        # We ignore the page_num parameter to prevent duplicate scraping
        if page_num > 1:
            # Return empty list for any page beyond first to stop pagination
            return []

        url = f"{self.base_url}/search?city={self.location}"

        soup = self.get_page_content(url)
        if not soup:
            self.logger.error("Failed to get content from %s", url)
            return []

        listings = []

        # Look for property items - they are in div.location elements
        property_items = soup.select("div.location")

        for item in property_items:
            try:
                # Extract the property link and address
                link_element = item.select_one("h2.heading-sm a.see-page-button")
                if not link_element:
                    self.logger.debug("No link element found in property item")
                    continue

                relative_url = link_element.get("href", "").strip()
                if not relative_url:
                    self.logger.debug("No href found in link element")
                    continue

                property_url = urljoin(self.base_url, relative_url)
                address = self.clean_text(link_element.text)

                # Extract city/location - look for postal code and city
                location_element = item.select_one("p.color-medium.fixed-lh")
                location = self.clean_text(
                    location_element.text if location_element else None
                )

                # Extract city name from location (remove postal code)
                city = self._extract_city_from_location(location)

                # Extract rental price
                price_element = item.select_one(
                    "p.heading-md.text-regular.color-primary"
                )
                price_text = self.clean_text(
                    price_element.text if price_element else None
                )
                rental_price = self.extract_rental_price(price_text)

                # Extract surface area
                surface_area = "N/A"
                area_elements = item.select("ul li")
                for li in area_elements:
                    li_text = self.clean_text(li.text)
                    if "woonoppervlakte" in li_text.lower() and "m²" in li_text:
                        # Extract the number before "m²"
                        area_match = re.search(r"(\d+)\s*m²", li_text)
                        if area_match:
                            surface_area = f"{area_match.group(1)} m²"
                        break

                # Only add if we have the essential data
                if address and address.lower() != "n/a":
                    # For Nederwoon, make the address more unique by including the URL ID
                    # to avoid duplicate filtering of different properties on the same street
                    unique_address = address
                    if property_url:
                        # Extract the ID from the URL (e.g., /36852/ from the URL)
                        url_id_match = re.search(r"/(\d+)/", property_url)
                        if url_id_match:
                            unique_address = f"{address} ({url_id_match.group(1)})"

                    listing = {
                        "adres": unique_address,
                        "link": property_url,
                        "naam_dorp_stad": city,
                        "huurprijs": rental_price,
                        "oppervlakte": surface_area,
                    }
                    listings.append(listing)
                    self.logger.debug("Added property: %s", unique_address)

            except (AttributeError, TypeError, ValueError) as e:
                self.logger.warning("Error extracting property data: %s", e)
                continue

        self.logger.info(
            "Found %d properties on Nederwoon %s", len(listings), self.location
        )
        return listings

    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """Retrieve detailed information about a specific rental property from Nederwoon.

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
            address_element = soup.select_one("h1, h2.heading-sm")
            if address_element:
                details["adres"] = self.clean_text(address_element.text)

            # Extract city/location
            location_element = soup.select_one("p.color-medium.fixed-lh")
            if location_element:
                location = self.clean_text(location_element.text)
                details["naam_dorp_stad"] = self._extract_city_from_location(location)

            # Extract rental price
            price_element = soup.select_one("p.heading-md.text-regular.color-primary")
            if price_element:
                price_text = self.clean_text(price_element.text)
                details["huurprijs"] = self.extract_rental_price(price_text)

            # Extract surface area from detail page
            details_sections = soup.select("ul li, .property-details li, .kenmerken li")
            for section in details_sections:
                section_text = self.clean_text(section.text)
                if "woonoppervlakte" in section_text.lower() and "m²" in section_text:
                    area_match = re.search(r"(\d+)\s*m²", section_text)
                    if area_match:
                        details["oppervlakte"] = f"{area_match.group(1)} m²"
                        break

        except (AttributeError, TypeError) as e:
            self.logger.error(
                "Error extracting property details from %s: %s", property_url, e
            )

        return details

    def _extract_city_from_location(self, location: str) -> str:
        """Extract city name from location string, removing postal code.

        Args:
            location: Location string like "3829DS Hooglanderveen"

        Returns:
            Clean city name
        """
        if not location or location == "N/A":
            return "N/A"

        # Remove postal code pattern (e.g. '3829DS ' or '1234 AB ')
        clean_location = re.sub(r"^\d{4}\s*[A-Z]{2}\s*", "", location)

        # Remove any remaining numbers and extra whitespace
        clean_location = re.sub(r"\d+", "", clean_location).strip()

        return clean_location if clean_location else "N/A"

    def get_all_listings(self, max_pages: int = 5) -> List[Dict[str, str]]:
        """
        Nederwoon doesn't support pagination, so we override this method to enforce max_pages=1

        Args:
            max_pages: Maximum number of pages to retrieve (ignored for Nederwoon)

        Returns:
            List of all found rental properties
        """
        return super().get_all_listings(max_pages=1)
