"""
Zonnenberg scraper module for scraping rental properties from the Zonnenberg Makelaardij website.
"""

import logging
import re
from typing import Dict, List
from urllib.parse import urljoin

import requests

from scrapers.base_scraper import BaseScraper

try:
    from bs4 import BeautifulSoup
except ImportError as exc:
    raise ImportError(
        "BeautifulSoup4 is required. Install it using 'pip install beautifulsoup4'"
    ) from exc

logger = logging.getLogger("WebScraper")


class ZonnenbergScraper(BaseScraper):
    """Scraper specifically for the Zonnenberg Makelaardij website."""

    def __init__(self):
        """Initialize the Zonnenberg scraper."""
        super().__init__("https://zonnenbergmakelaardij.nl")
        # Add extended headers to mimic a real browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "nl,en-US;q=0.7,en;q=0.3",
        }

    def get_property_listings(self) -> List[Dict[str, str]]:
        """Retrieve rental properties from the Zonnenberg website.

        Returns:
            List of dictionaries with rental property attributes.
        """

        # Zonnenberg loads all properties on a single page
        url = f"{self.base_url}/woningaanbod/huur/"

        # Gebruik een eigen requests sessie om meer controle te hebben
        session = requests.Session()
        response = session.get(url, headers=self.headers, timeout=30)
        if response.status_code != 200:
            logger.error(
                "Failed to get content from %s, status code: %s",
                url,
                response.status_code,
            )
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        if not soup:
            logger.error("Failed to parse HTML from %s", url)
            return []

        listings = []

        # Focus specifiek op article elementen
        property_items = soup.find_all("article")

        for item in property_items:
            try:
                # Find the link to the property detail page
                property_url = None
                links = item.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "woningaanbod/huur/" in href and "/page/" not in href:
                        property_url = href
                        break

                # If no link found in article, try parent
                if not property_url and item.parent and item.parent.name == "a":
                    property_url = item.parent.get("href", "")

                # If still no link, use article id to construct URL
                if not property_url or not property_url.startswith("http"):
                    property_id = item.get("id", "").replace("post-", "")
                    if property_id:
                        property_url = (
                            f"{self.base_url}/woningaanbod/huur/{property_id}/"
                        )

                # Make sure URL is absolute
                if property_url and not property_url.startswith("http"):
                    property_url = urljoin(self.base_url, property_url)

                # Skip invalid URLs
                if (
                    not property_url
                    or "/page/" in property_url
                    or property_url.endswith("/woningaanbod/huur/")
                ):
                    continue

                # Extract the basic properties directly from the article
                # Address
                address_element = item.select_one("h4")
                address = self.clean_text(
                    address_element.text if address_element else "N/A"
                )

                # Price
                price_element = item.select_one("span.price")
                price = self.clean_text(price_element.text if price_element else "N/A")

                # Place - directe extractie uit het artikel
                place_element = item.select_one("span.d-block.place")
                place = "N/A"
                if place_element:
                    place_text = self.clean_text(place_element.text)
                    # Strip postcode (4 cijfers gevolgd door 2 letters)
                    place = re.sub(r"^\d{4}\s*[A-Z]{2}\s*", "", place_text)

                # Area - directe extractie uit het artikel
                area_element = item.select_one("span.dimension")
                area = self.clean_text(area_element.text if area_element else "N/A")

                # Create the property dictionary
                property_data = {
                    "adres": address,
                    "link": property_url,
                    "naam_dorp_stad": place,
                    "huurprijs": price,
                    "oppervlakte": area,
                }

                # Add to listings
                listings.append(property_data)

            except (AttributeError, TypeError, KeyError) as e:
                logger.error("Error processing property: %s", e)
                continue

        # Verwijder duplicaten
        seen_addresses = set()
        unique_listings = []

        for listing in listings:
            address = listing.get("adres", "")
            if address and address not in seen_addresses and address.lower() != "login":
                seen_addresses.add(address)
                unique_listings.append(listing)

        return unique_listings

    def get_property_details(self, property_url: str) -> Dict[str, str]:
        """Retrieve detailed information about a specific rental property from Zonnenberg.

        Args:
            property_url: URL of the rental property.

        Returns:
            Dictionary with attributes of the rental property.
        """
        try:
            response = requests.get(property_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except (requests.RequestException, ValueError) as e:
            logger.error("Fout bij ophalen %s: %s", property_url, e)
            return {
                "adres": "N/A",
                "naam_dorp_stad": "N/A",
                "huurprijs": "N/A",
                "oppervlakte": "N/A",
                "link": property_url,
            }

        details = {
            "adres": "N/A",
            "naam_dorp_stad": "N/A",
            "huurprijs": "N/A",
            "oppervlakte": "N/A",
            "link": property_url,
        }

        try:
            # Get address
            address_element = soup.select_one(
                "h1.property-title, h1, .object-title, .address, .property-address"
            )
            if address_element:
                details["adres"] = self.clean_text(address_element.text)

            # Get location
            location_element = soup.select_one("span.d-block.place")
            if location_element:
                location_text = self.clean_text(location_element.text)
                # Strip postcode (4 cijfers gevolgd door 2 letters)
                details["naam_dorp_stad"] = re.sub(
                    r"^\d{4}\s*[A-Z]{2}\s*", "", location_text
                )

            # Get price
            price_element = soup.select_one("span.price")
            if price_element:
                details["huurprijs"] = self.clean_text(price_element.text)

            # Get surface area
            area_element = soup.select_one("span.dimension")
            if area_element:
                details["oppervlakte"] = self.clean_text(area_element.text)

            # Als we geen locatie hebben kunnen vinden, zoek in andere elementen
            if details["naam_dorp_stad"] == "N/A":
                # Zoek in metadata als dat beschikbaar is
                meta_location = soup.select_one('meta[property="og:locality"]')
                if meta_location and meta_location.get("content"):
                    details["naam_dorp_stad"] = self.clean_text(
                        meta_location.get("content")
                    )
                else:
                    # Zoek in de adrestekst
                    location_match = re.search(
                        r"\b\d{4}\s*[A-Z]{2}\b\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                        details["adres"],
                    )
                    if location_match and location_match.group(1):
                        details["naam_dorp_stad"] = location_match.group(1)

            # Als we geen oppervlakte hebben kunnen vinden, zoek in andere elementen
            if details["oppervlakte"] == "N/A":
                # Zoek naar tekst die lijkt op oppervlakte
                for element in soup.find_all(["span", "div"]):
                    text = element.text.strip()
                    if "m²" in text or "m2" in text or "㎡" in text:
                        # Voorkom dat we prijzen of andere metrische gegevens pakken
                        if not (
                            "€" in text
                            or "euro" in text
                            or "EUR" in text
                            or "prijs" in text.lower()
                        ):
                            size_match = re.search(r"(\d+)\s*(?:m²|m2|㎡)", text)
                            if size_match:
                                details["oppervlakte"] = f"{size_match.group(1)}m²"
                                break

        except (AttributeError, TypeError) as e:
            logger.error("Error retrieving details from %s: %s", property_url, e)

        return details
