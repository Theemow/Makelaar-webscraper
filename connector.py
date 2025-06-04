"""
connector voor de HuurhuisWebscraper.

Deze module coördineert tussen de webscraper en de database.
Het verwerkt de geschraapte data en slaat nieuwe listings op in de database.
"""

import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Dict, List, Set, Tuple

# Import the logging service
from log_service import LogService, get_logger
from scrapers.base_scraper import BaseScraper

# Importeer de scraper modules
from scrapers.scraper_factory import ScraperFactory

# Configure logger for this module
logger = get_logger("connector")


class Connector:
    """
    connector tussen webscraper en database.

    Verantwoordelijk voor:
    1. Aansturen van de scrapers
    2. Vergelijken van data tussen scraper en database
    3. Bijwerken van de database met nieuwe gegevens
    4. Bijhouden van nieuwe en verwijderde listings
    """

    def __init__(self, db_connection):
        """
        Initialiseer de connector.

        Args:
            db_connection: DataAccess object voor database-operaties
        """
        self.db = db_connection
        self.nieuwe_listings = []  # Houdt nieuwe listings bij voor rapportages
        self.processed_addresses: Set[str] = (
            set()
        )  # Set om adressen bij te houden die al zijn verwerkt
        self.log_service = LogService()  # Get the singleton instance

        # Thread safety
        self.result_lock = (
            threading.Lock()
        )  # Lock for threadsafe access to shared resources

    def verwerk_broker(
        self, broker_naam: str, scraper_type: str, broker_url: str = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Verwerk een makelaar door data te scrapen en de database bij te werken.

        Args:
            broker_naam: Naam van de makelaar
            scraper_type: Type scraper (bijvoorbeeld 'vdbunt', 'pararius')
            broker_url: URL van de makelaar (optioneel, alleen nodig bij nieuwe makelaars)

        Returns:
            Tuple containing (nieuwe_properties, verwijderde_properties)
        """
        thread_name = threading.current_thread().name
        logger.info("Verwerken van makelaar begonnen")

        # 1. Controleer of de broker bestaat, zo niet maak deze aan
        broker = self.db.get_broker_agency_by_name(broker_naam)
        if not broker:
            if not broker_url:
                raise ValueError(
                    f"Broker URL is required for new broker: {broker_naam}"
                )

            logger.info("Makelaar wordt aangemaakt")
            # We gebruiken de BrokerAgency class uit het notebook via een factory function
            broker = self._create_broker_agency(None, broker_naam, broker_url)
            broker_id = self.db.create_new_broker_agency(broker)
            broker.id = broker_id

        # 2. Haal een scraper op voor dit type broker
        scraper = self._get_scraper(scraper_type)

        # 3. Scrape alle properties van de website
        scraped_properties = self._scrape_properties(scraper)
        logger.info(
            f"Makelaar {broker_naam} ({scraper_type}) heeft {len(scraped_properties)} woningen gescraped (voor filtering)."
        )

        # 4. Haal alle bestaande properties op uit de database
        db_properties = self.db.get_properties_for_broker(broker.id)

        # 5. Vergelijk de data en categoriseer deze
        nieuwe_properties, _, verwijderde_properties = self._vergelijk_data(
            scraped_properties, db_properties
        )

        # Return alleen de resultaten zonder database updates uit te voeren
        # De daadwerkelijke updates zullen later gecoördineerd worden vanuit de hoofdthread

        # 7. Bewaar unieke nieuwe properties voor rapportage op basis van combinatie van kenmerken
        # ipv alleen adres
        unique_nieuwe_listings = []
        processed_property_keys = set()
        for prop in nieuwe_properties:
            adres = prop.get("adres", "").strip().lower()
            link = prop.get("link", "").strip().lower()
            huurprijs = prop.get("huurprijs", 0)

            # Maak een unieke sleutel voor deze property
            unique_key = (adres, link, str(huurprijs))

            if unique_key not in processed_property_keys:
                processed_property_keys.add(unique_key)
                # Add broker_id to property for later processing
                prop["broker_id"] = broker.id
                unique_nieuwe_listings.append(prop)

        # Log summary for this broker
        self.log_service.log_broker_processing(
            broker_naam, len(unique_nieuwe_listings), len(verwijderde_properties)
        )

        return unique_nieuwe_listings, verwijderde_properties

    def parallel_process_brokers(
        self, brokers: List[Dict], max_workers=None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Verwerk meerdere makelaars parallel met multithreading.

        Args:
            brokers: Lijst met dictionaries die broker informatie bevatten (naam, type, url)
            max_workers: Maximum aantal threads (standaard is None, wat betekent CPUs*5)

        Returns:
            Tuple met (alle_nieuwe_properties, alle_verwijderde_properties)
        """
        logger.info(
            f"Starting parallel processing of {len(brokers)} brokers with max_workers={max_workers}"
        )

        all_nieuwe_properties = []
        all_verwijderde_properties = []
        futures_to_broker = {}

        # Gebruik ThreadPoolExecutor om de makelaars parallel te verwerken
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Start scraping jobs voor elke makelaar
            for broker in brokers:
                # Name threads for better logging
                thread_name = f"Thread-{broker['naam']}"

                # Submit broker to thread pool
                future = executor.submit(
                    self._thread_wrapper,
                    broker["naam"],
                    broker["type"],
                    broker["url"],
                    thread_name,
                )
                futures_to_broker[future] = broker["naam"]

            # Verwerk de resultaten wanneer ze beschikbaar komen
            for future in as_completed(futures_to_broker):
                broker_name = futures_to_broker[future]
                try:
                    nieuwe, verwijderde = future.result()

                    # Thread-safe update of the combined results
                    with self.result_lock:
                        # Add broker name to each property for email grouping
                        for prop in nieuwe:
                            prop["broker_naam"] = broker_name

                        all_nieuwe_properties.extend(nieuwe)
                        all_verwijderde_properties.extend(verwijderde)

                except Exception as exc:
                    logger.error(f"Broker {broker_name} generated an exception: {exc}")

        logger.info(
            f"Parallel processing completed - Found {len(all_nieuwe_properties)} new and {len(all_verwijderde_properties)} removed properties"
        )
        return all_nieuwe_properties, all_verwijderde_properties

    def _thread_wrapper(self, broker_naam, scraper_type, broker_url, thread_name):
        """
        Wrapper function for threading to set thread name.
        """
        # Set thread name for logging
        threading.current_thread().name = thread_name
        return self.verwerk_broker(broker_naam, scraper_type, broker_url)

    def apply_database_updates(self, nieuwe_properties, verwijderde_properties):
        """
        Apply all database updates in a synchronized manner.
        This should be called from the main thread after parallel scraping is complete.

        Args:
            nieuwe_properties: List of new properties to add
            verwijderde_properties: List of properties to remove
        """
        logger.info(
            f"Applying database updates - {len(nieuwe_properties)} new, {len(verwijderde_properties)} removed"
        )

        # Process new properties
        for prop in nieuwe_properties:
            try:
                # Get the broker_id that was attached during scraping
                broker_id = prop.get("broker_id")
                if not broker_id:
                    logger.error(
                        f"Missing broker_id for property: {prop.get('adres', 'unknown')}"
                    )
                    continue

                self._verwerk_nieuwe_properties([prop], broker_id)

            except Exception as e:
                logger.error(f"Error processing new property: {e}")

        # Process removed properties
        for prop in verwijderde_properties:
            try:
                self._verwerk_verwijderde_properties([prop])
            except Exception as e:
                logger.error(f"Error processing removed property: {e}")

        # Store for reporting
        with self.result_lock:
            self.nieuwe_listings.extend(nieuwe_properties)

        return len(nieuwe_properties), len(verwijderde_properties)

    def _get_scraper(self, scraper_type: str) -> BaseScraper:
        """
        Haal een scraper op van het juiste type.

        Args:
            scraper_type: Type scraper (bijvoorbeeld 'vdbunt', 'pararius')

        Returns:
            Een scraper-instantie
        """
        try:
            return ScraperFactory.get_scraper(scraper_type)
        except ValueError as e:
            logger.error("Fout bij ophalen scraper: %s", e)
            raise

    def _scrape_properties(
        self, scraper: BaseScraper, max_pages: int = 5
    ) -> List[Dict[str, str]]:
        """
        Scrape alle properties van een website.

        Args:
            scraper: De scraper om te gebruiken
            max_pages: Maximaal aantal pagina's om te scrapen

        Returns:
            Lijst met gescrapede properties
        """
        try:
            return scraper.get_all_listings(max_pages=max_pages)
        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Fout bij scrapen van properties: %s", e)
            return []

    def _vergelijk_data(self, scraped_properties, db_properties):
        """
        Vergelijk gescrapede data met database-data.

        Args:
            scraped_properties: Properties van de scraper
            db_properties: Properties uit de database

        Returns:
            Tuple met (nieuwe_properties, bestaande_properties, verwijderde_properties)
        """
        # Apply price filters from configuration if enabled
        scraped_properties = self._apply_price_filters(scraped_properties)

        # Maak een dictionary van database properties om duplicaten te vinden
        # We gebruiken nu een combinatie van adres, link en prijs als unieke sleutel
        db_properties_dict = {}

        for prop in db_properties:
            # Gebruik een tuple van kenmerken als unieke identificatie
            unique_key = (
                prop.adres.strip().lower() if prop.adres else "",
                prop.link.strip().lower() if prop.link else "",
                str(prop.huurprijs) if prop.huurprijs is not None else "",
            )
            db_properties_dict[unique_key] = prop

        # Categoriseer de data
        nieuwe_properties = []
        bestaande_properties = []
        scraped_unique_keys = set()
        # Set om dubbele geschraapte properties te detecteren
        seen_scraped_keys = set()
        for prop in scraped_properties:
            adres = prop.get("adres", "").strip().lower()
            link = prop.get("link", "").strip().lower()
            huurprijs = prop.get("huurprijs", 0)

            # Maak een unieke sleutel voor deze property
            unique_key = (adres, link, str(huurprijs))

            # Als we deze property al eerder hebben gezien in de huidige scrape-run, skip
            if unique_key in seen_scraped_keys:
                logger.debug(
                    "Duplicate geschraapte property overgeslagen: %s", prop.get("adres")
                )
                continue

            # Markeer deze property als gezien
            seen_scraped_keys.add(unique_key)

            # Houd bij welke unique keys we hebben gezien voor het bepalen van verwijderde properties
            scraped_unique_keys.add(unique_key)

            # Als deze combinatie van kenmerken al bestaat, is het een bestaande property
            if unique_key in db_properties_dict:
                bestaande_properties.append(prop)
            else:
                nieuwe_properties.append(prop)

        # Vind verwijderde properties - properties die in de database staan maar niet in de scraped data
        verwijderde_properties = []
        for unique_key, prop in db_properties_dict.items():
            if unique_key not in scraped_unique_keys:
                verwijderde_properties.append(prop)

        logger.info(
            "Nieuwe properties: %d, Bestaande properties: %d, Te verwijderen properties: %d",
            len(nieuwe_properties),
            len(bestaande_properties),
            len(verwijderde_properties),
        )

        return nieuwe_properties, bestaande_properties, verwijderde_properties

    def _verwerk_nieuwe_properties(self, nieuwe_properties, broker_id):
        """
        Verwerk nieuwe properties door ze aan de database toe te voegen.

        Args:
            nieuwe_properties: Lijst met nieuwe properties
            broker_id: ID van de makelaar
        """
        vandaag = date.today()

        # Bijhouden van al toegevoegde properties binnen deze functie-aanroep
        # om dubbele logging te voorkomen
        added_property_keys = set()

        # Bestaande properties ophalen om te controleren op dubbele invoer
        bestaande_properties = self.db.get_properties_for_broker(broker_id)
        bestaande_property_keys = set()

        # Database property keys maken voor snelle controle
        for prop in bestaande_properties:
            bestaande_property_keys.add(
                (
                    prop.adres.strip().lower() if prop.adres else "",
                    prop.link.strip().lower() if prop.link else "",
                    str(prop.huurprijs) if prop.huurprijs is not None else "",
                )
            )

        for prop in nieuwe_properties:
            try:
                adres = prop.get("adres", "").strip().lower()
                link = prop.get("link", "").strip().lower()
                huurprijs = prop.get("huurprijs", 0)

                # Maak een unieke sleutel voor deze property
                unique_key = (adres, link, str(huurprijs))

                # Sla over als we deze property al hebben toegevoegd in deze run
                if unique_key in added_property_keys:
                    logger.debug(
                        "Property wordt overgeslagen (duplicaat in huidige run): %s",
                        prop["adres"],
                    )
                    continue

                # Sla over als de property al in de database bestaat
                if unique_key in bestaande_property_keys:
                    logger.debug(
                        "Property wordt overgeslagen (bestaat al in database): %s",
                        prop["adres"],
                    )
                    continue

                # Markeer als toegevoegd
                added_property_keys.add(unique_key)

                # Converteer het dictionary naar een Property object via een factory functie
                property_obj = self._create_property(
                    makelaardij_id=broker_id,
                    adres=prop["adres"],
                    link=prop["link"],
                    toegevoegd_op=vandaag,
                    naam_dorp_stad=prop["naam_dorp_stad"],
                    huurprijs=prop["huurprijs"],
                    oppervlakte=prop["oppervlakte"],
                )

                # Voeg toe aan de database
                self.db.create_new_rental_property(property_obj)
                logger.debug("Nieuwe property toegevoegd: %s", prop["adres"])

            except KeyError as e:
                logger.error("Ontbrekende key in property data: %s", e)
            except (ValueError, AttributeError) as e:
                logger.error(
                    "Fout bij toevoegen van property %s: %s",
                    prop.get("adres", "unknown"),
                    e,
                )

    def _verwerk_verwijderde_properties(self, verwijderde_properties):
        """
        Verwerk verwijderde properties door ze uit de database te verwijderen.

        Args:
            verwijderde_properties: Lijst met verwijderde properties
        """
        for prop in verwijderde_properties:
            try:
                self.db.remove_property(prop.makelaardij_id, prop.adres)
                logger.debug("Property verwijderd: %s", prop.adres)
            except (ValueError, AttributeError) as e:
                logger.error("Fout bij verwijderen van property %s: %s", prop.adres, e)

    def rapporteer_nieuwe_listings(self):
        """
        Geef een lijst van alle nieuwe listings die zijn gevonden.

        Returns:
            Lijst met nieuwe Property-objecten
        """
        return self.nieuwe_listings

    def verstuur_email_met_nieuwe_listings(self, mail_service, recipients):
        """
        Verstuur een e-mail met nieuwe listings die zijn gevonden.

        Args:
            mail_service: De mail service die gebruikt wordt om e-mails te versturen
            recipients: Een lijst van e-mailadressen of een enkel e-mailadres van de ontvangers

        Returns:
            bool: True als er een e-mail is verzonden, anders False
        """
        if not self.nieuwe_listings:
            logger.info("Geen nieuwe woningen gevonden, geen e-mail verzonden.")
            return False

        try:
            mail_success = mail_service.send_new_properties_email(
                recipients, self.nieuwe_listings
            )

            return mail_success
        except (ValueError, AttributeError) as e:
            logger.error("Fout bij het versturen van de e-mail: %s", e)
            self.log_service.log_email_sent(False, [])
            return False

    def _apply_price_filters(self, properties):
        """
        Filter properties based on price settings from the configuration.

        Args:
            properties: List of properties to filter

        Returns:
            Filtered list of properties
        """
        try:
            # Import config here to avoid circular imports
            from webscraper_config import FILTERS

            # Skip filtering if global filtering is disabled
            if not FILTERS.get("FILTERING_ENABLED", False):
                return properties

            filtered_properties = []

            # Apply max price filter if enabled
            max_price_filter = FILTERS.get(
                "MAX_PRICE_FILTER", {"enabled": False, "max_price": 0}
            )

            if max_price_filter.get("enabled", False):
                max_price = max_price_filter.get("max_price", 0)

                for prop in properties:
                    price = prop.get("huurprijs", 0)

                    # Skip properties with no price
                    if price == 0:
                        filtered_properties.append(prop)
                        continue

                    # Only include properties with price less than or equal to max_price
                    if price <= max_price:
                        filtered_properties.append(prop)
                    else:
                        logger.debug(
                            f"Property filtered out due to price (€{price} > €{max_price}): {prop.get('adres', 'unknown')}"
                        )

                return filtered_properties

            # If max price filter is disabled, return all properties
            return properties

        except (ImportError, KeyError) as e:
            logger.error(f"Error applying price filters: {e}")
            # If there's an error, return the original list
            return properties

    # Factory functies die Property en BrokerAgency objecten maken met de juiste klassen
    # Deze worden geïmplementeerd in de HuurhuisWebscraper notebook
    def _create_broker_agency(self, broker_id, naam, link):
        """Factory functie die een BrokerAgency object aanmaakt met de klasse uit het notebook."""
        # Deze wordt geïmplementeerd in het notebook
        # Return a dummy object until implemented in notebook
        return type("BrokerAgency", (), {"id": broker_id, "naam": naam, "link": link})

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
        """Factory functie die een Property object aanmaakt met de klasse uit het notebook."""
        # Deze wordt geïmplementeerd in het notebook
        # Return a dummy object until implemented in notebook
        return type(
            "Property",
            (),
            {
                "makelaardij_id": makelaardij_id,
                "adres": adres,
                "link": link,
                "toegevoegd_op": toegevoegd_op,
                "naam_dorp_stad": naam_dorp_stad,
                "huurprijs": huurprijs,
                "oppervlakte": oppervlakte,
            },
        )


def main():
    """Hoofdfunctie die de connector aanstuurt."""
    # Get the logging service
    log_service = LogService()

    # Voor standalone gebruik, importeer DataAccess vanuit HuurhuisWebscraper.ipynb
    try:
        # Probeer de DataAccess klasse te importeren uit notebook_utils
        # Commented out to prevent import errors since notebook_utils may not exist
        # from notebook_utils import DataAccess, MailService
        # Use dummy classes instead
        DataAccess = type("DataAccess", (), {})
        MailService = type("MailService", (), {})
    except ImportError:
        logger.error(
            "Om deze script standalone te gebruiken, moet je de DataAccess klasse importeren"
        )
        logger.error(
            "uit de HuurhuisWebscraper.ipynb. Voeg het volgende toe aan een bestand notebook_utils.py:"
        )
        logger.error(
            "from HuurhuisWebscraper import DataAccess, BrokerAgency, Property, MailService"
        )
        return []

    # Initialiseer de database-verbinding
    db = DataAccess()

    # Initialiseer de connector
    communicatie = Connector(db)

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
            "url": "https://www.pararius.nl/huurwoningen/amsterdam/",
        },
    ]
    # Process brokers in parallel
    alle_nieuwe_properties, alle_verwijderde_properties = (
        communicatie.parallel_process_brokers(makelaars)
    )

    # Apply database updates synchronously
    added_properties, removed_properties = communicatie.apply_database_updates(
        alle_nieuwe_properties, alle_verwijderde_properties
    )

    # Verstuur e-mail met nieuwe listings
    if alle_nieuwe_properties:
        try:
            # E-mailconfiguratie uit webscraper_config.py halen
            try:
                from webscraper_config import EMAIL

                sender_email = EMAIL["sender_email"]
                sender_password = EMAIL["sender_password"]
                recipients = EMAIL[
                    "recipients"
                ]  # Nu wordt de lijst met ontvangers gebruikt
                smtp_server = EMAIL["smtp_server"]
                smtp_port = EMAIL["smtp_port"]
            except ImportError:
                logger.error("Config.py niet gevonden. E-mail wordt niet verzonden.")
                return  # Stop verdere verwerking als config niet gevonden wordt
            except KeyError as e:
                logger.error(
                    "Ontbrekende configuratiesleutel in config.py: %s. E-mail wordt niet verzonden.",
                    e,
                )
                return  # Stop verdere verwerking als er een sleutel mist

            # Initialiseer de mail service
            mail_service = MailService(
                sender_email, sender_password, smtp_server, smtp_port
            )

            # Verstuur e-mail met nieuwe listings
            communicatie.verstuur_email_met_nieuwe_listings(mail_service, recipients)

        except (ImportError, KeyError, ValueError) as e:
            logger.error("Fout bij het versturen van de e-mail: %s", e)

    # Log application end with statistics
    log_service.log_app_end(
        len(alle_nieuwe_properties), len(alle_verwijderde_properties)
    )

    return alle_nieuwe_properties


if __name__ == "__main__":
    main()
