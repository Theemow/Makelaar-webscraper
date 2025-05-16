"""
VastgoedNederland scraper module for scraping rental properties from the VastgoedNederland website.
"""

from typing import Dict, List
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper


class VastgoedNederlandScraper(BaseScraper):
    """Scraper specifically for the VastgoedNederland website."""

    def __init__(self, location: str = "veenendaal"):
        """Initialize the VastgoedNederland scraper with a specific location.

        Args:
            location: The location to search for properties (default: veenendaal)
        """
        super().__init__("https://aanbod.vastgoednederland.nl")
        self.location = location

    def get_property_listings(self, page_num: int = 1) -> List[Dict[str, str]]:
        """Retrieve rental properties from the VastgoedNederland website.

        Args:
            page_num: Page number to retrieve.

        Returns:
            List of dictionaries with rental property attributes.
        """
        # Construct URL with pagination
        url = f"{self.base_url}/huurwoningen?q={self.location}&straal=15000"

        # Add pagination parameter if not the first page
        if page_num > 1:
            url += f"&p={page_num}"

        soup = self.get_page_content(url)
        if not soup:
            self.logger.warning(f"Failed to retrieve content from {url}")
            return []

        listings = []

        # Find all property items - they are in div.col-12.col-sm-6.col-lg-4 elements
        property_items = soup.select("div.col-12.col-sm-6.col-lg-4")

        for item in property_items:
            try:
                # Get the link element
                link_element = item.select_one("a.propertyLink")
                if not link_element:
                    continue

                property_url = link_element.get("href", "")
                if not property_url:
                    continue

                # Get the property details
                figure = link_element.select_one("figure.property")
                if not figure:
                    continue

                # Get the address (street)
                street_element = figure.select_one("figcaption span.street")
                street = self.clean_text(
                    street_element.text if street_element else None
                )

                # Get the location (city)
                city_element = figure.select_one("figcaption span.city")
                city = self.clean_text(city_element.text if city_element else None)

                # Get the rental price
                price_element = figure.select_one("figcaption span.price")
                price = self.clean_text(price_element.text if price_element else None)

                # Get the surface area
                area_element = figure.select_one(
                    "figcaption div.bottom ul li:first-child"
                )
                area = "N/A"
                if area_element:
                    # Extract just the area value, e.g., "120m²" from the element that contains an icon and the text
                    area_text = self.clean_text(area_element.text)
                    # The text might contain an icon class name, so we clean it up
                    area = area_text.replace("icon-meter", "").strip() or "N/A"

                listings.append(
                    {
                        "adres": street,
                        "link": property_url,
                        "naam_dorp_stad": city,
                        "huurprijs": price,
                        "oppervlakte": area,
                    }
                )

            except (AttributeError, TypeError, ValueError) as e:
                self.logger.error(f"Error processing property: {e}")
                continue

        # Check if there are more pages
        next_page_link = soup.select_one(
            "ul.pagination li.page-item:last-child:not(.disabled) a"
        )
        has_next_page = next_page_link is not None

        if not has_next_page and page_num == 1 and not listings:
            self.logger.warning("No properties found and no pagination detected")

        return listings

    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """Retrieve detailed information about a specific rental property.

        Args:
            property_url: URL of the rental property.

        Returns:
            Dictionary with attributes of the rental property.
        """

        soup = self.get_page_content(property_url)
        if not soup:
            self.logger.warning(
                f"Failed to retrieve property details from {property_url}"
            )
            return {}

        details = {}

        # Basic property information should already be collected in get_property_listings
        # This method could be expanded to gather additional details from the property page

        # For now, we'll just return a basic structure
        return {
            "url": property_url,
            "last_updated": "N/A",  # This could be updated if available on the page
        }
