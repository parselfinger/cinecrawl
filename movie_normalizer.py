import re

import requests

from logging_config import get_logger

logger = get_logger(__name__)


def strip_screening_format(title: str) -> str:
    """
    Remove screening format suffixes from movie titles.

    Strips suffixes like ': VIP', ': IMAX', ': 3D', ': 4DX' etc.
    These are screening formats, not part of the actual movie title.

    Args:
        title: Original movie title

    Returns:
        Title with screening format suffixes removed

    Examples:
        >>> strip_screening_format("Colors of Fire: VIP")
        "Colors of Fire"
        >>> strip_screening_format("Warlord: Olori Ogun")
        "Warlord: Olori Ogun"  # Keeps meaningful subtitles
        >>> strip_screening_format("Mufasa: IMAX 3D")
        "Mufasa"
    """
    # Common screening formats to strip
    # Use word boundaries to avoid stripping from actual subtitles
    # IMPORTANT: Order matters! Check combined formats before individual ones
    screening_formats = [
        r":\s*IMAX\s+3D\b",  # Check "IMAX 3D" before "IMAX" or "3D"
        r":\s*4DX\s+3D\b",  # Check "4DX 3D" before "4DX" or "3D"
        r":\s*VIP\b",
        r":\s*IMAX\b",
        r":\s*3D\b",
        r":\s*4DX\b",
    ]

    cleaned = title
    for pattern in screening_formats:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Clean up any trailing whitespace
    cleaned = cleaned.strip()

    if cleaned != title:
        logger.debug(f"Stripped format suffix: '{title}' → '{cleaned}'")

    return cleaned


class MovieNormalizer:
    def __init__(self):
        pass

    def search_imdb(self, title: str, year: int | None = None) -> dict | None:
        """
        Search IMDB Dev API for movie and return best match.

        Uses title similarity and year matching to score results.

        Args:
            title: Movie title to search for
            year: Optional release year for better matching

        Returns:
            Normalized movie dict or None if no good match found
        """
        try:
            query = f"{title} {year}" if year else title
            params = {"query": query}
            response = requests.get(
                "https://api.imdbapi.dev/search/titles",
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            titles = data.get("titles", [])
            if not titles:
                logger.debug(f"No IMDB results for '{title}'")
                return None

            # Filter to movies only
            movies = [t for t in titles if t.get("type") == "movie"]
            if not movies:
                logger.debug(
                    f"No movie results for '{title}' "
                    f"(found {len(titles)} non-movie results)"
                )
                return None

            best_match = movies[0]

            # Extract data from best match
            primary_image = best_match.get("primaryImage", {})
            rating_data = best_match.get("rating", {})

            normalized = {
                "source": "imdb",
                "tmdb_id": None,
                "imdb_id": best_match.get("id"),
                "title": best_match.get("primaryTitle"),
                "description": None,  # Not available in search endpoint
                "release_year": (
                    int(best_match.get("startYear"))
                    if best_match.get("startYear")
                    else None
                ),
                "duration_minutes": None,  # Not available in search endpoint
                "rating": (
                    float(rating_data.get("aggregateRating"))
                    if rating_data and rating_data.get("aggregateRating")
                    else None
                ),
                "poster_url": (primary_image.get("url") if primary_image else None),
            }

            logger.info(
                f"[IMDB] Found match: '{title}' → '{normalized['title']}' "
                f"({normalized['release_year']}, IMDB ID: {normalized['imdb_id']})"
            )

            return normalized

        except Exception as e:
            logger.warning(f"IMDB search failed for '{title}': {type(e).__name__}: {e}")
            return None

    def normalize_title(self, title: str, year: int | None = None) -> dict:
        """
        Get normalized movie data from IMDB Dev API.

        Args:
            title: Movie title from cinema scraper
            year: Optional release year

        Returns:
            Dict with movie data (normalized if found, original if not)
        """
        # Strip screening format suffixes before normalization
        cleaned_title = strip_screening_format(title)

        # Try IMDB Dev API
        imdb_data = self.search_imdb(cleaned_title, year)
        if imdb_data:
            return imdb_data

        # Fallback to cleaned title (not original with VIP/IMAX suffix)
        logger.warning(f"No IMDB match for '{cleaned_title}', using cleaned title")
        return {
            "source": "original",
            "tmdb_id": None,
            "imdb_id": None,
            "title": cleaned_title,
            "description": None,
            "release_year": year,
            "duration_minutes": None,
            "rating": None,
            "poster_url": None,
        }


_movie_cache: dict[str, dict] = {}


def get_normalized_movie(title: str, year: int | None = None) -> dict:
    """
    Get normalized movie data from IMDB Dev API with session caching.

    Cache prevents hitting the API multiple times for the same movie in a single scrape.
    Example: If 5 cinemas show "Mufasa", we only call IMDB once.

    Args:
        title: Movie title from cinema scraper
        year: Optional release year

    Returns:
        Dict with normalized movie data
    """
    # Clean title before caching to ensure "Movie: VIP" and "Movie" use same cache
    cleaned_title = strip_screening_format(title)
    cache_key = f"{cleaned_title.lower().strip()}:{year}"

    if cache_key in _movie_cache:
        logger.debug(f"Session cache hit for '{cleaned_title}'")
        return _movie_cache[cache_key]

    normalizer = MovieNormalizer()
    movie_data = normalizer.normalize_title(cleaned_title, year)

    _movie_cache[cache_key] = movie_data

    return movie_data
