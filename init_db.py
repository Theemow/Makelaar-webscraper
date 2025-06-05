"""
Dit script initialiseert de database schema voor de HuurhuisWebscraper.
Het maakt de benodigde tabellen aan als ze nog niet bestaan.
"""

import psycopg2
import time
from webscraper_config import DATABASE

# Import the centralized logging service instead of configuring basic logging
from log_service import get_logger

logger = get_logger(__name__)


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
            logger.info("Wachten op database... Poging %d/%d", attempt + 1, max_retries)
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
        cursor = connection.cursor()  # Create sequences first if they don't exist
        cursor.execute(
            """
        CREATE SEQUENCE IF NOT EXISTS broker_agencies_broker_id_seq
            INCREMENT 1
            START 1
            MINVALUE 1
            MAXVALUE 2147483647
            CACHE 1;

        CREATE SEQUENCE IF NOT EXISTS property_property_id_seq
            INCREMENT 1
            START 1
            MINVALUE 1
            MAXVALUE 2147483647
            CACHE 1;
        """
        )

        # Maak broker_agencies tabel aan
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS public.broker_agencies
        (
            broker_id integer NOT NULL DEFAULT nextval('broker_agencies_broker_id_seq'::regclass),
            broker_name text COLLATE pg_catalog."default" NOT NULL,
            hyperlink text COLLATE pg_catalog."default" NOT NULL,
            CONSTRAINT broker_agencies_pkey PRIMARY KEY (broker_id)
        )
        """
        )

        # Maak properties tabel aan
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS public.property
        (
            property_id integer NOT NULL DEFAULT nextval('property_property_id_seq'::regclass),
            broker_id integer,
            adres text COLLATE pg_catalog."default",
            hyperlink text COLLATE pg_catalog."default",
            price text COLLATE pg_catalog."default",
            size text COLLATE pg_catalog."default",
            last_seen date DEFAULT CURRENT_DATE,
            CONSTRAINT property_pkey PRIMARY KEY (property_id),
            CONSTRAINT broker FOREIGN KEY (broker_id)
                REFERENCES public.broker_agencies (broker_id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION
        )
        """
        )

        # Voeg last_seen kolom toe aan bestaande property tabellen als deze nog niet bestaat
        cursor.execute(
            """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'property' 
                AND column_name = 'last_seen'
                AND table_schema = 'public'
            ) THEN
                ALTER TABLE public.property ADD COLUMN last_seen date DEFAULT CURRENT_DATE;
            END IF;
        END $$;
        """
        )  # Controleer of er tabellen zijn aangemaakt
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = cursor.fetchall()
        logger.info("Aangemaakte tabellen: %s", [table[0] for table in tables])

        cursor.close()
        connection.close()

        logger.info("Database schema is succesvol geïnitialiseerd.")
        return True

    except (psycopg2.Error, psycopg2.OperationalError) as e:
        logger.error("Fout bij het initialiseren van het database schema: %s", e)
        return False


if __name__ == "__main__":
    logger.info("Database initialisatie script wordt uitgevoerd...")
    success = init_database()
    if success:
        logger.info("Database initialisatie voltooid.")
    else:
        logger.error("Database initialisatie mislukt.")
