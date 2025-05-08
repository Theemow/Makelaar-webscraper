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
        """Initialize database connection using settings from config.py."""
        # Import config here to avoid circular imports
        from config import DATABASE

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
                    INSERT INTO "BrokerAgencies" ("BrokerName", "Hyperlink")
                    VALUES (%s, %s)
                    RETURNING "BrokerId"
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
                    INSERT INTO "Property" ("BrokerId", "Adres", "Hyperlink", "Price", "Size")
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
                    SELECT "BrokerId", "BrokerName", "Hyperlink"
                    FROM "BrokerAgencies"
                    WHERE "BrokerName" = %s
                    """,
                    (agency_name,),
                )
                result = cursor.fetchone()
                if result:
                    return BrokerAgency(id=result[0], naam=result[1], link=result[2])
                return None

    def get_broker_agency(self, agency_id: int) -> Optional[BrokerAgency]:
        """Get a broker agency by ID."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT "BrokerId", "BrokerName", "Hyperlink"
                    FROM "BrokerAgencies"
                    WHERE "BrokerId" = %s
                    """,
                    (agency_id,),
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
                    SELECT "BrokerId", "Adres", "Hyperlink", CURRENT_DATE, 'Onbekend', "Price", "Size"
                    FROM "Property"
                    WHERE "BrokerId" = %s
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

    def get_all_properties(self) -> List[Property]:
        """Get all properties in the database."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT "BrokerId", "Adres", "Hyperlink", CURRENT_DATE, 'Onbekend', "Price", "Size"
                    FROM "Property"
                    """
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

    def get_all_properties_for_location(self, location: str) -> List[Property]:
        """Get all properties for a specific location."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT "BrokerId", "Adres", "Hyperlink", CURRENT_DATE, 'Onbekend', "Price", "Size"
                    FROM "Property"
                    WHERE "NaamDorpStad" = %s
                    """,
                    (location,),
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

    # Update Operations
    def update_property(self, prop: Property) -> None:
        """Update a property in the database."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE "Property"
                    SET "Price" = %s, "Size" = %s
                    WHERE "BrokerId" = %s AND "Adres" = %s
                    """,
                    (prop.huurprijs, prop.oppervlakte, prop.makelaardij_id, prop.adres),
                )

    def update_broker_agency(self, agency: BrokerAgency) -> None:
        """Update a broker agency in the database."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE "BrokerAgencies"
                    SET "BrokerName" = %s, "Hyperlink" = %s
                    WHERE "BrokerId" = %s
                    """,
                    (agency.naam, agency.link, agency.id),
                )

    # Delete Operations
    def remove_property(self, makelaardij_id: int, adres: str) -> None:
        """Remove a property from the database."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM "Property"
                    WHERE "BrokerId" = %s AND "Adres" = %s
                    """,
                    (makelaardij_id, adres),
                )

    def remove_broker_agency(self, agency_id: int) -> None:
        """Remove a broker agency from the database."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # First remove all properties associated with this agency
                cursor.execute(
                    """
                    DELETE FROM "Property"
                    WHERE "BrokerId" = %s
                    """,
                    (agency_id,),
                )
                # Then remove the agency itself
                cursor.execute(
                    """
                    DELETE FROM "BrokerAgencies"
                    WHERE "BrokerId" = %s
                    """,
                    (agency_id,),
                )
