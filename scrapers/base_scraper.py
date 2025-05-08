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
    raise ImportError("BeautifulSoup4 is required. Install it using 'pip install beautifulsoup4'") from exc

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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
            self.logger.info("Retrieving page: %s", url)
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
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
        return re.sub(r'\s+', ' ', text).strip() or "N/A"
    
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
                self.logger.info("Processing page %d", page)
                page_listings = self.get_property_listings(page)
                if not page_listings:
                    self.logger.info("No more results found on page %d. Stopping.", page)
                    break
                
                # Check for duplicate listings by address
                unique_listings = []
                duplicate_count = 0
                
                for listing in page_listings:
                    address = listing.get('adres', '')
                    if address and address not in seen_addresses:
                        seen_addresses.add(address)
                        unique_listings.append(listing)
                    else:
                        duplicate_count += 1
                
                # If all listings on this page are duplicates, stop scraping
                if duplicate_count == len(page_listings):
                    self.logger.info("All %d listings on page %d are duplicates. Stopping pagination.", 
                                duplicate_count, page)
                    break
                
                # Add only unique listings to our results
                all_listings.extend(unique_listings)
                self.logger.info("Page: %d | Found new: %d | Duplicates: %d",
                           page, len(unique_listings), duplicate_count)
                
            except (requests.RequestException, ValueError, KeyError) as e:
                self.logger.error("Error processing page %d: %s", page, e)
                break
                
        self.logger.info("Total properties found: %d", len(all_listings))
        return all_listings