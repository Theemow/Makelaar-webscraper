"""
Factory module for creating scraper instances based on website names.
"""

from typing import Dict, Type

from scrapers.base_scraper import BaseScraper
from scrapers.vdbunt_scraper import VdBuntScraper
from scrapers.pararius_scraper import ParariusScraper
from scrapers.zonnenberg_scraper import ZonnenbergScraper
from scrapers.ditters_scraper import DittersScraper

class ScraperFactory:
    """Factory class to create the right scraper based on the website name."""
    
    _SCRAPERS: Dict[str, Type[BaseScraper]] = {
        "vdbunt": VdBuntScraper,
        "pararius": ParariusScraper,
        "zonnenberg": ZonnenbergScraper,
        "ditters": DittersScraper,
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
        
        if website in ScraperFactory._SCRAPERS:
            return ScraperFactory._SCRAPERS[website]()
        else:
            available_scrapers = ", ".join(ScraperFactory._SCRAPERS.keys())
            raise ValueError(f"No scraper available for website: {website}. Available scrapers: {available_scrapers}")