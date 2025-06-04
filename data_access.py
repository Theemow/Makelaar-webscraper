# filepath: c:\Users\User\Documents\GitHub\Makelaar-webscraper\data_access.py
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import psycopg2


@dataclass
class BrokerAgency:
    """Class for keeping track of broker agencies."""

    id: Optional[int]
    naam: str
    link: str


@dataclass
class Property:
    """Class for keeping track of rental properties."""

    makelaardij_id: int
    adres: str
    link: str
    toegevoegd_op: date
    naam_dorp_stad: str
    huurprijs: str
    oppervlakte: str


class DataAccess:
    def __init__(self):
        """Initialize database connection using settings from webscraper_config.py."""
        # Import config here to avoid circular imports
        from webscraper_config import DATABASE

        self.connection_params = {
            "dbname": DATABASE["dbname"],
            "user": DATABASE["user"],
            "password": DATABASE["password"],
            "host": DATABASE["host"],
            "port": DATABASE["port"],
        }

    def get_connection(self):
        """Create and return a database connection."""
        return psycopg2.connect(**self.connection_params)

    # Create Operations
    def create_new_broker_agency(self, agency: BrokerAgency) -> int:
        """Create a new broker agency and return its ID."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO broker_agencies (broker_name, hyperlink)
                    VALUES (%s, %s)
                    RETURNING broker_id
                    """,
                    (agency.naam, agency.link),
                )
                return cursor.fetchone()[0]

    def create_new_rental_property(self, prop: Property) -> None:
        """Create a new rental property."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO property (broker_id, adres, hyperlink, price, size)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        prop.makelaardij_id,
                        prop.adres,
                        prop.link,
                        prop.huurprijs,
                        prop.oppervlakte,
                    ),
                )

    # Read Operations
    def get_broker_agency_by_name(self, agency_name: str) -> Optional[BrokerAgency]:
        """Get a broker agency by name."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT broker_id, broker_name, hyperlink
                    FROM broker_agencies
                    WHERE broker_name = %s
                    """,
                    (agency_name,),
                )
                result = cursor.fetchone()
                if result:
                    return BrokerAgency(id=result[0], naam=result[1], link=result[2])
                return None

    def get_properties_for_broker(self, agency_id: int) -> List[Property]:
        """Get all properties for a specific broker agency."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT broker_id, adres, hyperlink, CURRENT_DATE, 'Onbekend', price, size
                    FROM property
                    WHERE broker_id = %s
                    """,
                    (agency_id,),
                )
                results = cursor.fetchall()
                return [
                    Property(
                        makelaardij_id=row[0],
                        adres=row[1],
                        link=row[2],
                        toegevoegd_op=row[3],
                        naam_dorp_stad=row[4],
                        huurprijs=row[5],
                        oppervlakte=row[6],
                    )
                    for row in results
                ]

    # Delete Operations
    def remove_property(self, makelaardij_id: int, adres: str) -> None:
        """Remove a property from the database."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM property
                    WHERE broker_id = %s AND adres = %s
                    """,
                    (makelaardij_id, adres),
                )
