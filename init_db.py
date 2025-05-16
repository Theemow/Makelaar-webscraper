"""
Dit script initialiseert de database schema voor de HuurhuisWebscraper.
Het maakt de benodigde tabellen aan als ze nog niet bestaan.
"""

import psycopg2
from psycopg2 import sql
import logging
import time
from config import DATABASE

# Configureer logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_db():
    """Wacht tot de database beschikbaar is."""
    max_retries = 30
    retry_interval = 2

    for attempt in range(max_retries):
        try:
            connection = psycopg2.connect(
                dbname=DATABASE["dbname"],
                user=DATABASE["user"],
                password=DATABASE["password"],
                host=DATABASE["host"],
                port=DATABASE["port"],
            )
            connection.close()
            logger.info("Database is beschikbaar. Verbinding succesvol.")
            return True
        except psycopg2.OperationalError:
            logger.info(f"Wachten op database... Poging {attempt + 1}/{max_retries}")
            time.sleep(retry_interval)

    logger.error("Kon geen verbinding maken met de database na meerdere pogingen.")
    return False


def init_database():
    """Maakt de benodigde tabellen aan als ze nog niet bestaan."""
    if not wait_for_db():
        return False

    try:
        # Maak verbinding met de database
        connection = psycopg2.connect(
            dbname=DATABASE["dbname"],
            user=DATABASE["user"],
            password=DATABASE["password"],
            host=DATABASE["host"],
            port=DATABASE["port"],
        )
        connection.autocommit = True
        cursor = connection.cursor()

        # Maak broker_agencies tabel aan
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS broker_agencies (
            id SERIAL PRIMARY KEY,
            naam VARCHAR(255) NOT NULL,
            website VARCHAR(255) NOT NULL,
            laatste_verwerking TIMESTAMP
        )
        """
        )

        # Maak properties tabel aan
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS properties (
            id SERIAL PRIMARY KEY,
            adres VARCHAR(255) NOT NULL,
            naam_dorp_stad VARCHAR(255),
            huurprijs VARCHAR(255),
            oppervlakte VARCHAR(255),
            link VARCHAR(512),
            broker_agency_id INTEGER REFERENCES broker_agencies(id),
            datum_toegevoegd DATE DEFAULT CURRENT_DATE,
            is_nieuw BOOLEAN DEFAULT TRUE,
            CONSTRAINT unique_property UNIQUE (adres, broker_agency_id)
        )
        """
        )

        # Controleer of er tabellen zijn aangemaakt
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = cursor.fetchall()
        logger.info(f"Aangemaakte tabellen: {[table[0] for table in tables]}")

        cursor.close()
        connection.close()

        logger.info("Database schema is succesvol geïnitialiseerd.")
        return True

    except Exception as e:
        logger.error(f"Fout bij het initialiseren van het database schema: {e}")
        return False


if __name__ == "__main__":
    logger.info("Database initialisatie script wordt uitgevoerd...")
    success = init_database()
    if success:
        logger.info("Database initialisatie voltooid.")
    else:
        logger.error("Database initialisatie mislukt.")
