# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

CineCrawl is an async Python web scraper that collects cinema showtimes from Nigerian cinema chains. It normalizes movie data via the IMDB Dev API and stores results in PostgreSQL. The system supports both direct scraping and AWS Lambda deployment.

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_validation.py

# Run with verbose output
pytest -v

# Run async tests
pytest tests/test_utils.py -v
```

### Code Quality
```bash
# Format code with black
black .

# Lint with ruff
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Running the Scraper
```bash
# Run locally (requires .env with DATABASE_URL and FILMHOUSE_SECRET_KEY)
python main.py

# The script will:
# - Fetch showtimes from enabled providers
# - Validate and deduplicate results
# - Normalize movie titles via IMDB API
# - Save to PostgreSQL
# - Clean up old showtimes (>7 days)
```

## Architecture

### Provider Pattern
All cinema scrapers inherit from `BaseProvider` (providers/base.py) and implement:
- `async fetch() -> list[Showtime]`: Main scraping logic
- `cinema_name`: Cinema chain name
- `location`: Specific location
- `display_name`: Auto-generated "cinema_name, location"

**Provider types:**
1. **API-based**: FilmHouse (encrypted payload via api/external), FusionIntel (bearer tokens)
2. **HTML scraping**: Silverbird, Genesis, BluePictures (BeautifulSoup)

Each provider has concrete implementations per location (e.g., `FilmHouseLandmarkProvider`, `GenesisMarylandProvider`). To add a new location, subclass the base provider and set the location-specific properties.

### Data Flow
```
main.py orchestrates:
1. Concurrent provider fetching (asyncio.gather)
2. Validation (validation.py) - checks required fields, filters past dates
3. Deduplication (validation.py) - by (cinema, title, datetime)
4. Movie cache initialization (movie_cache.py):
   - Loads all movies from database into memory at startup
   - Enables fast fuzzy matching without database queries
5. Movie normalization (movie_normalizer.py):
   - In-memory cache with fuzzy matching (85% similarity threshold)
   - Session-level cache prevents duplicate API calls
   - Cache check → API call → database insert → add to cache
   - IMDB Dev API search by title + year
6. Database persistence (db.py):
   - get_or_create_movie: Checks cache with fuzzy matching, then normalizes via API
   - get_or_create_cinema: Upserts cinema records
   - save_showtimes_to_db: Inserts with duplicate handling
7. Cleanup: Deletes showtimes older than 7 days
```

### Database Schema (PostgreSQL)
```sql
movies: id, title, description, release_year, duration_minutes, rating, poster_url
cinemas: id, name, location
showtimes: id, movie_id (FK), cinema_id (FK), start_time, screen_type
```

**Key constraint**: Unique index on (movie_id, cinema_id, start_time) prevents duplicates.

### Error Handling
- `retry.py`: `@async_retry` decorator for network failures (3 attempts, exponential backoff)
- `exceptions.py`: `AuthenticationError` for missing API credentials
- Provider errors don't crash the entire scrape - logged and reported in final stats

### Models (models.py)
- `Showtime`: Core dataclass with cinema, location, title, time (string), date (datetime), year (int), screen_type
- `CinemaResult`: Wrapper for provider results with success/error tracking

## Key Implementation Details

### Provider API Authentication
**FilmHouse**: Uses encrypted payload via `api/external` endpoint
- POST to `https://www.filmhouseng.com/api/external` with `{"payload": "<base64>"}`
- Payload is AES-256-CBC encrypted (OpenSSL-compatible, EVP_BytesToKey with MD5)
- Inner payload: `{endpoint, method, data, headers, langId}` → routes to cms_widget/index
- See `_encrypt_payload()` in providers/filmhouse.py

**FusionIntel**: Bearer token passed in Authorization header
- Used by: Viva, EbonyLife, Ozone, Sky, THC cinemas
- See `fetch_fusionintel_showtimes()` in providers/utils.py

### HTML Parsing Patterns
**Silverbird**: Day ranges ("FRI-SUN") expanded via `_expand_day_range()`
- Parses relative weekday ranges from current date
- Handles various formats: "MON", "MONDAY", "MON-WED"

**Genesis**: Requires fetching movie detail pages for release year
- Implements year caching to avoid redundant fetches
- Two-step process: list page → detail page per movie

### Movie Cache and Fuzzy Matching
The `MovieCache` class (movie_cache.py) provides intelligent movie matching with these features:

**Architecture**:
- Loads all movies from database into memory at startup (1 query for entire dataset)
- Uses rapidfuzz for fuzzy string matching with 85% similarity threshold
- Automatically handles variants: "Colors of Fire" matches "Colors of Fire: VIP"
- Case-insensitive matching with punctuation tolerance
- Year-based preference when multiple matches exist

**Performance Benefits**:
- **Genesis/Grand/BluePictures**: Eliminates per-movie HTTP requests for detail pages when movie is cached
- **Database queries**: 1 query at startup vs 2+ queries per movie without cache
- **Lambda warm starts**: Cache persists across invocations in warm containers
- **Fuzzy matching**: Natural handling of typos, suffixes (": VIP", " IMAX"), and spelling variants

**Lookup Flow** (db.py:16-95):
1. **Cache check**: Fuzzy match against in-memory movies (rapidfuzz 85% threshold)
2. **Cache miss**: Normalize via IMDB Dev API (session-cached)
3. **Insert new movie**: Add to database and cache for future lookups

This architecture minimizes both database queries and API calls - returning to just the cache after the first scrape.

### AWS Lambda Support
Single Lambda, event-driven. Handler: `main.lambda_handler`

| Event | Action |
|-------|--------|
| `{}` or `{"action": "scrape"}` | Fetch showtimes, save to DB |
| `{"action": "enrich"}` | OMDB enrichment (poster, description, ratings) |

Configure two EventBridge rules with different event payloads for different schedules.

## Environment Variables
Required in `.env`:
```
DATABASE_URL=postgresql://user:pass@host:port/db
FILMHOUSE_SECRET_KEY=xxx  # For FilmHouse API payload encryption (AES passphrase)
OMDB_API_KEY=xxx         # Optional: For enriching movies with poster, description, ratings
```

## Adding New Providers

1. **API provider**: Subclass `BaseProvider`, implement `fetch()` with `@async_retry`
2. **HTML provider**: Use `httpx.AsyncClient` + `BeautifulSoup`, apply retry decorator
3. **Location-specific**: Subclass the base cinema provider, set `cinema_name`, `location`, and ID
4. Add instance to `PROVIDERS` list in main.py

Example for new Genesis location:
```python
class GenesisNewLocationProvider(GenesisProvider):
    cinema_name = "Genesis Deluxe Cinemas"
    location = "New Mall, Lagos"
    cinema_id = "12"  # From Genesis API
```

## Testing Patterns
- Use `pytest` fixtures for datetime mocking
- Async tests require `@pytest.mark.asyncio` decorator
- Test validation logic with edge cases (missing fields, past dates, duplicates)
- Mock external API calls in unit tests

## Python Version
Requires Python 3.13+ (uses modern type hints like `list[T]`, `dict[K, V]`)
