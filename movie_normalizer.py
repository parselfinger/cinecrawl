import os

import requests
import tmdbsimple as tmdb
from dotenv import load_dotenv

from logging_config import get_logger

load_dotenv()
logger = get_logger(__name__)

tmdb.API_KEY = os.getenv("TMDB_API_KEY")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")


class MovieNormalizer:
    def __init__(
        self, tmdb_api_key: str | None = None, omdb_api_key: str | None = None
    ):
        if tmdb_api_key:
            tmdb.API_KEY = tmdb_api_key

        self.omdb_api_key = omdb_api_key or OMDB_API_KEY

    def search_tmdb(self, title: str, year: int | None = None) -> dict | None:
        if not tmdb.API_KEY:
            logger.debug("TMDB_API_KEY not set, skipping TMDB search")
            return None

        try:
            search = tmdb.Search()

            if year:
                response = search.movie(query=title, year=year)
            else:
                response = search.movie(query=title)

            if not response["results"]:
                logger.debug(f"No TMDB results for '{title}'")
                return None

            # Get first result (best match)
            movie_data = response["results"][0]

            movie_id = movie_data["id"]
            movie = tmdb.Movies(movie_id)
            details = movie.info()

            normalized = {
                "source": "tmdb",
                "tmdb_id": details["id"],
                "imdb_id": details.get("imdb_id"),
                "title": details["title"],
                "description": details.get("overview"),
                "release_year": (
                    int(details["release_date"][:4])
                    if details.get("release_date")
                    else None
                ),
                "duration_minutes": details.get("runtime"),
                "rating": details.get("vote_average"),
                "poster_url": (
                    f"https://image.tmdb.org/t/p/w500{details['poster_path']}"
                    if details.get("poster_path")
                    else None
                ),
                "backdrop_url": (
                    f"https://image.tmdb.org/t/p/w1280{details['backdrop_path']}"
                    if details.get("backdrop_path")
                    else None
                ),
            }

            logger.info(
                f"[TMDB] Found match: '{title}' → '{normalized['title']}' "
                f"({normalized['release_year']}, TMDB ID: {normalized['tmdb_id']})"
            )

            return normalized

        except Exception as e:
            logger.warning(f"TMDB search failed for '{title}': {type(e).__name__}: {e}")
            return None

    def search_omdb(self, title: str, year: int | None = None) -> dict | None:
        if not self.omdb_api_key:
            logger.debug("OMDB_API_KEY not set, skipping OMDb search")
            return None

        try:
            params = {
                "apikey": self.omdb_api_key,
                "t": title,  # Search by title
                "type": "movie",
            }

            if year:
                params["y"] = year

            response = requests.get(
                "http://www.omdbapi.com/", params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "False":
                logger.debug(f"No OMDb results for '{title}': {data.get('Error')}")
                return None

            # Extract and normalize data
            normalized = {
                "source": "omdb",
                "tmdb_id": None,
                "imdb_id": data.get("imdbID"),
                "title": data.get("Title"),
                "description": data.get("Plot") if data.get("Plot") != "N/A" else None,
                "release_year": (
                    int(data.get("Year")[:4])
                    if data.get("Year") and data["Year"] != "N/A"
                    else None
                ),
                "duration_minutes": (
                    int(data.get("Runtime").split()[0])
                    if data.get("Runtime") and data["Runtime"] != "N/A"
                    else None
                ),
                "rating": (
                    float(data.get("imdbRating"))
                    if data.get("imdbRating") and data["imdbRating"] != "N/A"
                    else None
                ),
                "poster_url": (
                    data.get("Poster") if data.get("Poster") != "N/A" else None
                ),
                "backdrop_url": None,
            }

            logger.info(
                f"[OMDb] Found match: '{title}' → '{normalized['title']}' "
                f"({normalized['release_year']}, IMDB ID: {normalized['imdb_id']})"
            )

            return normalized

        except Exception as e:
            logger.warning(f"OMDb search failed for '{title}': {type(e).__name__}: {e}")
            return None

    def normalize_title(self, title: str, year: int | None = None) -> dict:
        """
        Get normalized movie data with fallback chain: TMDB → OMDb → original title.

        Args:
            title: Movie title from cinema scraper
            year: Optional release year

        Returns:
            Dict with movie data (normalized if found, original if not)
        """
        # Try TMDB first (best data, free, 50 req/sec)
        tmdb_data = self.search_tmdb(title, year)
        if tmdb_data:
            return tmdb_data

        # Fallback to OMDb (IMDB data, 1000 req/day free)
        logger.debug(f"TMDB not found for '{title}', trying OMDb...")
        omdb_data = self.search_omdb(title, year)
        if omdb_data:
            return omdb_data

        logger.warning(f"No API match for '{title}', using original title")
        return {
            "source": "original",
            "tmdb_id": None,
            "imdb_id": None,
            "title": title,
            "description": None,
            "release_year": year,
            "duration_minutes": None,
            "rating": None,
            "poster_url": None,
            "backdrop_url": None,
        }


_movie_cache: dict[str, dict] = {}


def get_normalized_movie(title: str, year: int | None = None) -> dict:
    """
    Get normalized movie data from TMDB/OMDb APIs with session caching.

    Cache prevents hitting the API multiple times for the same movie in a single scrape.
    Example: If 5 cinemas show "Mufasa", we only call TMDB once.

    Args:
        title: Movie title from cinema scraper
        year: Optional release year

    Returns:
        Dict with normalized movie data
    """
    cache_key = f"{title.lower().strip()}:{year}"

    if cache_key in _movie_cache:
        logger.debug(f"Cache hit for '{title}'")
        return _movie_cache[cache_key]

    normalizer = MovieNormalizer()
    movie_data = normalizer.normalize_title(title, year)

    _movie_cache[cache_key] = movie_data

    return movie_data
