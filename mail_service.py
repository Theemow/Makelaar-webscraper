import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import defaultdict

# Import the central logging service
from log_service import get_logger

# Get logger for this module
logger = get_logger("MailService")


class MailService:
    """Service voor het versturen van e-mails met informatie over nieuwe woningen."""

    def __init__(
        self, sender_email=None, sender_password=None, smtp_server=None, smtp_port=None
    ):
        """Initialiseer de mail service met instellingen uit config.py als standaard.

        Args:
            sender_email: Het e-mailadres van de afzender (standaard uit config.py)
            sender_password: Het wachtwoord of de app-specifieke code voor het e-mailadres (standaard uit config.py)
            smtp_server: De SMTP-server (standaard uit config.py)
            smtp_port: De SMTP-poort (standaard uit webscraper_config.py)
        """
        # Import config here to avoid circular imports
        from webscraper_config import EMAIL

        # Use values from webscraper_config.py as defaults
        self.sender_email = sender_email or EMAIL["sender_email"]
        self.sender_password = sender_password or EMAIL["sender_password"]
        self.smtp_server = smtp_server or EMAIL["smtp_server"]
        self.smtp_port = smtp_port or EMAIL["smtp_port"]

    def send_new_properties_email(self, recipients=None, nieuwe_properties=None):
        """Stuur een e-mail met nieuwe woningen.

        Args:
            recipients: Lijst van e-mailadressen of een enkel e-mailadres voor de ontvanger(s) (standaard uit config.py)
            nieuwe_properties: Lijst met nieuwe woningen

        Returns:
            bool: True als de e-mail succesvol is verzonden, anders False
        """
        if nieuwe_properties is None:
            nieuwe_properties = []

        if not nieuwe_properties:
            logger.info("Geen nieuwe woningen gevonden, geen e-mail verzonden.")
            return True

        # Import config here to avoid circular imports
        from webscraper_config import EMAIL

        # Use recipients from webscraper_config.py if not provided
        if recipients is None:
            recipients = EMAIL["recipients"]

        # Zorg ervoor dat recipients een lijst is, ook als er maar één ontvanger is
        if isinstance(recipients, str):
            recipients = [recipients]

        try:
            # Maak een nieuwe e-mail aan
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = ", ".join(
                recipients
            )  # Meerdere ontvangers scheiden met komma's
            msg["Subject"] = (
                f"Nieuwe Huurwoningen - {datetime.now().strftime('%d-%m-%Y %H:%M')}"
            )

            # Groepeer properties per makelaar
            properties_by_broker = self._group_properties_by_broker(nieuwe_properties)

            # Begin de HTML-inhoud
            html_content = f"""
            <html>
            <head>
                <style>
                    table {{border-collapse: collapse; width: 100%; margin-bottom: 30px;}}
                    th, td {{text-align: left; padding: 8px; border-bottom: 1px solid #ddd;}}
                    th {{background-color: #f2f2f2;}}
                    tr:hover {{background-color: #f5f5f5;}}
                    .price {{color: #e63946; font-weight: bold;}}
                    .address {{font-weight: bold;}}
                    h3 {{color: #2a6592; margin-top: 30px; margin-bottom: 10px;}}
                </style>
            </head>
            <body>
                <h2>Nieuwe Huurwoningen</h2>
                <p>Er zijn in totaal {len(nieuwe_properties)} nieuwe huurwoningen gevonden bij {len(properties_by_broker)} makelaars:</p>
            """

            # Voor elke makelaar een aparte tabel maken
            for broker_name, properties in properties_by_broker.items():
                html_content += f"""
                <h3>{broker_name} ({len(properties)} nieuwe woningen)</h3>
                <table>
                    <tr>
                        <th>Adres</th>
                        <th>Plaats</th>
                        <th>Oppervlakte</th>
                        <th>Huurprijs</th>
                    </tr>
                """

                # Voeg elke nieuwe woning van deze makelaar toe aan de tabel
                for prop in properties:
                    adres = prop.get("adres", "Onbekend")
                    plaats = prop.get("naam_dorp_stad", "Onbekend")
                    prijs = prop.get("huurprijs", "Onbekend")
                    oppervlakte = prop.get("oppervlakte", "Onbekend")
                    link = prop.get("link", "#")

                    html_content += f"""
                    <tr>
                        <td class="address"><a href="{link}">{adres}</a></td>
                        <td>{plaats}</td>
                        <td>{oppervlakte}</td>
                        <td class="price">{prijs}</td>
                    </tr>
                    """

                # Sluit deze tabel
                html_content += "</table>"

            # Sluit de HTML-inhoud af
            html_content += """
                <p>Dit bericht is automatisch gegenereerd door de HuurhuisWebscraper.</p>
            </body>
            </html>
            """

            # Voeg de HTML-inhoud toe aan de e-mail
            msg.attach(MIMEText(html_content, "html"))

            # Verbind met de SMTP-server en verstuur de e-mail
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Beveilig de verbinding
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            return True

        except (smtplib.SMTPException, ConnectionError, ValueError) as e:
            logger.error(f"Fout bij het verzenden van de e-mail: {e}")
            return False

    def _group_properties_by_broker(self, properties):
        """Groepeer properties per makelaar.

        Args:
            properties: Lijst met properties

        Returns:
            Dictionary met properties gegroepeerd per makelaar
        """
        result = defaultdict(list)

        for prop in properties:
            # Gebruik 'broker_naam' als dat beschikbaar is, anders gebruik makelaar_id
            broker_name = prop.get(
                "broker_naam", prop.get("makelaar_naam", "Onbekende makelaar")
            )
            result[broker_name].append(prop)

        return result

    def send_error_email(self, recipients=None, error_message=""):
        """Stuur een e-mail met een foutmelding.

        Args:
            recipients: Lijst van e-mailadressen of een enkel e-mailadres voor de ontvanger(s) (standaard uit config.py)
            error_message: De foutmelding

        Returns:
            bool: True als de e-mail succesvol is verzonden, anders False
        """
        # Import config here to avoid circular imports
        from webscraper_config import EMAIL

        # Use recipients from webscraper_config.py if not provided
        if recipients is None:
            recipients = EMAIL["recipients"]

        # Zorg ervoor dat recipients een lijst is, ook als er maar één ontvanger is
        if isinstance(recipients, str):
            recipients = [recipients]

        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = ", ".join(
                recipients
            )  # Meerdere ontvangers scheiden met komma's
            msg["Subject"] = (
                f"Fout in HuurhuisWebscraper - {datetime.now().strftime('%d-%m-%Y %H:%M')}"
            )

            html_content = f"""
            <html>
            <body>
                <h2>Er is een fout opgetreden in de HuurhuisWebscraper</h2>
                <p><strong>Foutmelding:</strong> {error_message}</p>
                <p>Dit bericht is automatisch gegenereerd door de HuurhuisWebscraper.</p>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(
                f"Foutmelding e-mail verzonden naar {len(recipients)} ontvanger(s)."
            )
            return True

        except (smtplib.SMTPException, ConnectionError, ValueError) as e:
            logger.error(f"Fout bij het verzenden van de foutmelding e-mail: {e}")
            return False
