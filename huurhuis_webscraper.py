#!/usr/bin/env python3

# Huurhuis webscraper
# Dit script is een webscraper die informatie verzamelt van verschillende makelaarswebsites
# Lees de readme.md voor meer informatie over de configuratie en het gebruik van deze scraper.

# Imports:
import psycopg2
from psycopg2 import sql
from datetime import date
from dataclasses import dataclass
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
import re
from urllib.parse import urljoin
from typing import Dict, List, Optional, Union, Any
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import logging
from datetime import datetime

# Import configuration
from webscraper_config import DATABASE, EMAIL

# Import mail service
from mail_service import MailService

# Import data access
from data_access import DataAccess, BrokerAgency, Property

# Import logging service
from log_service import LogService, get_logger


# Importeer de connector
from connector import Connector


# Uitbreiden van connector met factory functies voor onze datamodellen
class Huurhuisconnector(Connector):
    def _create_broker_agency(self, id, naam, link):
        """Factory functie die een BrokerAgency object aanmaakt met de klasse uit data_access.py."""
        return BrokerAgency(id=id, naam=naam, link=link)

    def _create_property(
        self,
        makelaardij_id,
        adres,
        link,
        toegevoegd_op,
        naam_dorp_stad,
        huurprijs,
        oppervlakte,
    ):
        """Factory functie die een Property object aanmaakt met de klasse uit data_access.py."""
        return Property(
            makelaardij_id=makelaardij_id,
            adres=adres,
            link=link,
            toegevoegd_op=toegevoegd_op,
            naam_dorp_stad=naam_dorp_stad,
            huurprijs=huurprijs,
            oppervlakte=oppervlakte,
        )


def run_scraper_proces():
    """Voer het volledige scraper proces uit."""
    # Initialize logging service
    log_service = LogService()
    logger = get_logger("HuurhuisWebscraper")

    # Initialiseer de database-verbinding
    db = DataAccess()

    # Initialiseer de connector met onze aangepaste versie
    communicatie = Huurhuisconnector(db)

    # Lijst met te verwerken makelaars en hun scraper-type
    makelaars = [
        {
            "naam": "Van Roomen Van de Bunt NVM Makelaars",
            "type": "vdbunt",
            "url": "https://www.vdbunt.nl/aanbod/woningaanbod/huur/",
        },
        {
            "naam": "Pararius",
            "type": "pararius",
            "url": "https://www.pararius.nl/huurwoningen/leusden/",
        },
        {
            "naam": "Zonnenberg Makelaardij",
            "type": "zonnenberg",
            "url": "https://zonnenbergmakelaardij.nl/woningaanbod/huur/",
        },
        {
            "naam": "Ditters Makelaars",
            "type": "ditters",
            "url": "https://www.ditters.nl/woningaanbod/?filter%5Bcategory%5D=%2FHuur",
        },
        {
            "naam": "InterHouse Utrecht",
            "type": "interhouse-utrecht",
            "url": "https://interhouse.nl/huurwoningen/?location_id=Utrecht_Algemeen&number_of_results=20&sort=date-desc&display=list",
        },
        {
            "naam": "InterHouse Amersfoort",
            "type": "interhouse-amersfoort",
            "url": "https://interhouse.nl/huurwoningen/?location_id=Amersfoort_Algemeen&number_of_results=20&sort=date-desc&display=list",
        },
        {
            "naam": "VastgoedNederland Veenendaal",
            "type": "vastgoednederland",
            "url": "https://aanbod.vastgoednederland.nl/huurwoningen?q=veenendaal&straal=15000",
        },
        {
            "naam": "VBT Verhuurmakelaars",
            "type": "vbt",
            "url": "https://vbtverhuurmakelaars.nl/woningen",
        },
    ]

    # Set main thread name for better logging
    threading.current_thread().name = "MainThread"

    # Process brokers in parallel and gather results
    # Use max_workers based on number of brokers - for 4 brokers, use 4 threads
    max_workers = len(makelaars)

    alle_nieuwe_properties, alle_verwijderde_properties = (
        communicatie.parallel_process_brokers(makelaars, max_workers=max_workers)
    )

    # After all scrapers have completed, synchronously apply database updates
    communicatie.apply_database_updates(
        alle_nieuwe_properties, alle_verwijderde_properties
    )

    # Verstuur mail met nieuwe woningen
    if alle_nieuwe_properties:
        logger.info(f"Sending email with {len(alle_nieuwe_properties)} new properties")

        # Initialiseer de mail service met de configuratie uit config.py
        mail_service = MailService()

        # Verstuur de mail met nieuwe woningen
        mail_success = mail_service.send_new_properties_email(
            None, alle_nieuwe_properties
        )

        if mail_success:
            logger.info(
                f"E-mail with {len(alle_nieuwe_properties)} new properties successfully sent to {len(EMAIL['recipients'])} recipient(s)"
            )
        else:
            logger.error("There was a problem sending the email.")

    # Log application end
    log_service.log_app_end(
        len(alle_nieuwe_properties), len(alle_verwijderde_properties)
    )


if __name__ == "__main__":
    run_scraper_proces()
