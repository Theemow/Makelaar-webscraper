# Docker gebruiken met Huurhuis Webscraper

Je kunt de Huurhuis Webscraper nu ook in een Docker container draaien, samen met een PostgreSQL database.

## Vereisten

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Installatie en gebruik

1. Clone deze repository (als je dat nog niet gedaan hebt):
   ```bash
   git clone https://github.com/yourusername/Makelaar-webscraper.git
   cd Makelaar-webscraper
   ```

2. Pas de config.py aan met je gewenste instellingen. De database-instellingen moeten overeenkomen met die in de docker-compose.yml:
   ```python
   # Database configuration
   DATABASE = {
       "dbname": "HuurhuizenWebscraper",  # Name of the database
       "user": "postgres",  # Database user
       "password": "admin",  # Database password
       "host": "postgres",  # Gebruik 'postgres' als hostnaam (naam van de Docker service)
       "port": "5432",  # Database port (default is 5432 for PostgreSQL)
   }
   ```

3. Start de containers:
   ```bash
   docker-compose up -d
   ```

4. Bekijk de logs:
   ```bash
   docker-compose logs -f webscraper
   ```

5. Stop de containers:
   ```bash
   docker-compose down
   ```

## Eenmalig uitvoeren

Als je de webscraper eenmalig wilt uitvoeren zonder de container te laten draaien:

```bash
docker-compose run --rm webscraper
```

## Gegevens en persistentie

- Alle logs worden opgeslagen in de ./logs map op je host.
- De config.py die je op je host hebt, wordt gebruikt in de container.
- PostgreSQL gegevens worden bewaard in een Docker volume genaamd postgres_data.

## Componenten aanpassen

Als je wijzigingen maakt aan de code, moet je de containers opnieuw bouwen:

```bash
docker-compose build
docker-compose up -d
```
