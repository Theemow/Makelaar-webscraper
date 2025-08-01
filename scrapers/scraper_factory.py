"""
Factory module for creating scraper instances based on website names.
"""

from typing import Dict, Type

from scrapers.base_scraper import BaseScraper
from scrapers.ditters_scraper import DittersScraper
from scrapers.interhouse_scraper import InterHouseScraper
from scrapers.nederwoon_scraper import NederwoonScraper
from scrapers.pararius_scraper import ParariusScraper
from scrapers.vdbunt_scraper import VdBuntScraper
from scrapers.vastgoednederland_scraper import VastgoedNederlandScraper
from scrapers.vbt_scraper import VBTScraper
from scrapers.zonnenberg_scraper import ZonnenbergScraper


class ScraperFactory:
    """Factory class to create the right scraper based on the website name."""

    _SCRAPERS: Dict[str, Type[BaseScraper]] = {
        "vdbunt": VdBuntScraper,
        "pararius": ParariusScraper,
        "zonnenberg": ZonnenbergScraper,
        "ditters": DittersScraper,
        "vastgoednederland": VastgoedNederlandScraper,
        "vbt": VBTScraper,
        "nederwoon": NederwoonScraper,
    }

    @staticmethod
    def get_scraper(website: str) -> BaseScraper:
        """Return a scraper instance for the requested website.

        Args:
            website: Name of the website (case-insensitive)

        Returns:
            A scraper instance for the requested website

        Raises:
            ValueError: If no scraper is available for the requested website
        """
        website = website.lower()

        # Special handling for interhouse with different locations
        if website == "interhouse-utrecht":
            return InterHouseScraper(location="Utrecht")
        elif website == "interhouse-amersfoort":
            return InterHouseScraper(location="Amersfoort")
        elif website == "interhouse":  # Default to Utrecht for backwards compatibility
            return InterHouseScraper(location="Utrecht")
        
        # Special handling for nederwoon with different locations
        elif website == "nederwoon-utrecht":
            return NederwoonScraper(location="Utrecht")
        elif website == "nederwoon-amersfoort":
            return NederwoonScraper(location="Amersfoort")
        elif website == "nederwoon":  # Default to Amersfoort for backwards compatibility
            return NederwoonScraper(location="Amersfoort")

        if website in ScraperFactory._SCRAPERS:
            return ScraperFactory._SCRAPERS[website]()
        else:
            available_scrapers = list(ScraperFactory._SCRAPERS.keys())
            available_scrapers.extend(
                ["interhouse", "interhouse-utrecht", "interhouse-amersfoort", 
                 "nederwoon", "nederwoon-utrecht", "nederwoon-amersfoort"]
            )
            available_scrapers_str = ", ".join(available_scrapers)
            raise ValueError(
                f"No scraper available for website: {website}. Available scrapers: {available_scrapers_str}"
            )
