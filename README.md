# CineCrawl

An async Python scraper that collects cinema showtimes from Nigerian cinema chains. Normalizes movie data via IMDB and OMDB APIs, stores results in PostgreSQL, and supports AWS Lambda deployment.

## Features

- **Multi-provider scraping**: FilmHouse, Genesis, Silverbird, Viva, EbonyLife, and more
- **Movie normalization**: IMDB Dev API for title matching and metadata
- **OMDB enrichment**: Poster URLs, descriptions, ratings (IMDB, Rotten Tomatoes, Metacritic)
- **Fuzzy matching**: In-memory cache with 85% similarity threshold for efficient lookups
- **Event-driven Lambda**: Single deployment, different actions via event payload

## Supported Cinemas

| Chain | Locations |
|-------|-----------|
| FilmHouse | Landmark, Lekki IMAX, Oniru, Palms Lekki, Surulere, Circle Mall, Ikota |
| Genesis Deluxe | Maryland, Festac, Lekki |
| Silverbird | Ikeja, Galleria |
| Viva | Ikeja, Lekki |
| EbonyLife, Sky, Ozone, THC | Various |
| BluePictures, Filmworld, Grand, Magnificent | Various |

## Prerequisites

- Python 3.13+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/cinecrawl.git
cd cinecrawl

# Install dependencies with uv
uv sync
```

## Configuration

Create a `.env` file in the project root:

```env
# Required for scraping
DATABASE_URL=postgresql://user:pass@host:port/db
FILMHOUSE_SECRET_KEY=xxx    # For FilmHouse API (get from network inspection)

# Optional: OMDB enrichment (poster, description, ratings)
OMDB_API_KEY=xxx            # Free at https://www.omdbapi.com/apikey.aspx
```

## Usage

### Local

```bash
# Scrape showtimes from all providers
uv run python main.py

# Scrape only (explicit)
uv run python main.py scrape

# Enrich movies with OMDB data (poster, description, ratings)
uv run python main.py enrich
```

### Database Migrations

```bash
# Run migrations
uv run alembic upgrade head

# Create new migration (with SQLAlchemy models)
uv run alembic revision --autogenerate -m "description"
```

### AWS Lambda

Deploy as a container image. The Lambda handler routes by `event["action"]`:

| Event | Action |
|-------|--------|
| `{}` or `{"action": "scrape"}` | Fetch showtimes, save to DB |
| `{"action": "enrich"}` | OMDB enrichment |

Configure EventBridge rules for different schedules (e.g. scrape every 6h, enrich daily).

## Project Structure

```
cinecrawl/
├── main.py              # Entry point, Lambda handler, scrape orchestration
├── omdb_enricher.py     # OMDB API enrichment
├── db.py                # Database operations
├── movie_cache.py       # In-memory fuzzy matching cache
├── movie_normalizer.py  # IMDB Dev API normalization
├── providers/           # Cinema scrapers (FilmHouse, Genesis, etc.)
├── app/                 # SQLAlchemy models for Alembic
├── alembic/             # Database migrations
└── tests/
```

## Development

```bash
# Run tests
uv run pytest -v

# Format and lint
uv run black .
uv run ruff check .
uv run ruff check --fix .

# Pre-commit
uv run pre-commit run --all-files
```

## License

MIT
