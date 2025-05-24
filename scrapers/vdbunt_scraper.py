"""
VdBunt scraper module for scraping rental properties from the VdBunt website.
"""

import logging
from typing import Dict, List
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger("WebScraper")


class VdBuntScraper(BaseScraper):
    """Scraper specifically for the VdBunt website."""

    def __init__(self):
        """Initialize the VdBunt scraper."""
        super().__init__("https://www.vdbunt.nl")

    def get_property_listings(self, page_num: int = 1) -> List[Dict[str, str]]:
        """Retrieve rental properties from the VdBunt website.

        Args:
            page_num: Page number to retrieve (ignored for VdBunt as they don't support pagination).

        Returns:
            List of dictionaries with rental property attributes.
        """
        # VdBunt doesn't support pagination, so we only fetch the first page
        # We ignore the page_num parameter to prevent duplicate scraping
        if page_num > 1:
            # Return empty list for any page beyond first to stop pagination
            return []

        url = f"{self.base_url}/aanbod/woningaanbod/huur/"

        soup = self.get_page_content(url)
        if not soup:
            return []

        listings = []

        # The website shows properties in li.al2woning.aanbodEntry elements
        property_items = soup.select("li.al2woning.aanbodEntry")

        for item in property_items:
            try:
                # Get the link to the property
                link_element = item.select_one("a.aanbodEntryLink")
                if not link_element:
                    continue

                property_url = urljoin(self.base_url, link_element.get("href", ""))

                # Get the address
                address_element = item.select_one("h3.street-address")
                address = self.clean_text(
                    address_element.text if address_element else None
                )

                # Location (city)
                location_element = item.select_one("span.locality")
                location = self.clean_text(
                    location_element.text if location_element else None
                )

                # Rental price - we look for the element with "huurprijs" as attribute
                price_element = item.select_one(
                    "span.kenmerk.huurprijs span.kenmerkValue"
                )
                price_text = self.clean_text(
                    price_element.text if price_element else None
                )
                price_numeric = self.extract_rental_price(
                    price_text
                )  # Surface area - we look for the element with "woonoppervlakte" as attribute
                area_element = item.select_one(
                    "span.kenmerk.woonoppervlakte span.kenmerkValue"
                )
                area = self.clean_text(area_element.text if area_element else None)

                listings.append(
                    {
                        "adres": address,
                        "link": property_url,
                        "naam_dorp_stad": location,
                        "huurprijs": price_numeric,
                        "oppervlakte": area,
                    }
                )

            except (AttributeError, TypeError, ValueError) as e:
                logger.error("Error processing property: %s", e)
                continue

        return listings

    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """Retrieve detailed information about a specific rental property from VdBunt.

        Args:
            property_url: URL of the rental property.

        Returns:
            Dictionary with attributes of the rental property.
        """
        soup = self.get_page_content(property_url)
        if not soup:
            return {
                "adres": "N/A",
                "naam_dorp_stad": "N/A",
                "huurprijs": "N/A",
                "oppervlakte": "N/A",
                "link": property_url,
            }

        details = {}

        try:
            # Address
            address_element = soup.select_one("h1.street-address, h1.obj-address")
            details["adres"] = self.clean_text(
                address_element.text if address_element else None
            )

            # Location
            location_element = soup.select_one("span.locality")
            details["naam_dorp_stad"] = self.clean_text(
                location_element.text if location_element else None
            )

            # Rental price - we adjust the selector for the detail page
            price_element = soup.select_one(
                ".kenmerk.huurprijs .kenmerkValue, .obj-kenmerken.first .huurprijs .rechts"
            )
            price_text = self.clean_text(price_element.text if price_element else None)
            details["huurprijs"] = self.extract_rental_price(price_text)

            # Surface area - we adjust the selector for the detail page
            details["oppervlakte"] = "N/A"  # Default value

            area_element = soup.select_one(
                ".kenmerk.woonoppervlakte .kenmerkValue, .obj-kenmerken .woonoppervlakte .rechts"
            )
            if area_element:
                details["oppervlakte"] = self.clean_text(area_element.text)

            details["link"] = property_url

        except (AttributeError, TypeError) as e:
            logger.error("Error retrieving details from %s: %s", property_url, e)

        return details

    # Override get_all_listings to force max_pages=1 for VdBunt
    def get_all_listings(self, max_pages: int = 5) -> List[Dict[str, str]]:
        """
        VdBunt doesn't support pagination, so we override this method to enforce max_pages=1

        Args:
            max_pages: Maximum number of pages to retrieve (ignored for VdBunt)

        Returns:
            List of all found rental properties
        """
        return super().get_all_listings(max_pages=1)
