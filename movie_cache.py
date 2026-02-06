"""In-memory movie cache with fuzzy matching for efficient movie lookups."""

import psycopg2
from rapidfuzz import fuzz

from logging_config import get_logger

logger = get_logger(__name__)

# Global cache instance for provider access
_global_cache = None


def get_global_cache():
    """Get the global movie cache instance."""
    return _global_cache


def set_global_cache(cache):
    """Set the global movie cache instance."""
    global _global_cache
    _global_cache = cache


class MovieCache:
    """
    In-memory cache of movies for fast fuzzy matching.

    Loads all movies from database at startup to avoid repeated queries.
    Uses rapidfuzz for intelligent title matching that handles variants,
    punctuation differences, and common suffixes.
    """

    def __init__(self):
        """Initialize empty cache."""
        self._movies: dict[int, dict] = {}  # movie_id -> {title, year}

    def load_from_db(self, database_url: str) -> None:
        """
        Load all movies from database into memory.

        Args:
            database_url: PostgreSQL connection string
        """
        conn = psycopg2.connect(database_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, release_year FROM movies ORDER BY id")
                rows = cur.fetchall()

                for movie_id, title, year in rows:
                    self._movies[movie_id] = {
                        "title": title,
                        "year": year,
                    }

            logger.info(f"Loaded {len(self._movies)} movies into cache")

        finally:
            conn.close()

    def find_match(
        self, title: str, year: int | None = None
    ) -> tuple[int, str, int | None] | None:
        """
        Find best matching movie using fuzzy matching.

        Uses rapidfuzz to match titles with 85% similarity threshold.
        Prefers movies with matching year as tiebreaker.

        Special handling for titles with colons (e.g., "Movie: Subtitle"):
        - Compares against both full title and prefix before colon
        - Allows "Warlord" to match "Warlord: Olori Ogun"
        - Allows "Agesinkole 2" to match "Agesinkole 2: King of Thieves"

        Args:
            title: Movie title to search for
            year: Optional release year for better matching

        Returns:
            Tuple of (movie_id, db_title, db_year) if match found, None otherwise

        Examples:
            >>> cache.find_match("Colors of Fire")
            (123, "Colors of Fire: VIP", 2024)
            >>> cache.find_match("Mufaza")  # typo
            (456, "Mufasa", 2024)
            >>> cache.find_match("Warlord")
            (789, "Warlord: Olori Ogun", 2024)
        """
        if not self._movies:
            logger.debug("Cache is empty, no matches possible")
            return None

        best_match = None
        best_score = 0
        threshold = 85

        for movie_id, movie_data in self._movies.items():
            db_title = movie_data["title"]
            db_year = movie_data["year"]

            # Calculate similarity score against full title
            score = fuzz.ratio(title.lower(), db_title.lower())

            # If database title has a colon, also check prefix match
            # This handles "Warlord" matching "Warlord: Olori Ogun"
            if ":" in db_title:
                prefix = db_title.split(":", 1)[0].strip()
                prefix_score = fuzz.ratio(title.lower(), prefix.lower())
                # Use the better score between full title and prefix
                score = max(score, prefix_score)

            # Boost score if years match
            if year and db_year == year:
                score += 5  # Year match bonus

            if score > best_score and score >= threshold:
                best_score = score
                best_match = (movie_id, db_title, db_year)

        if best_match:
            movie_id, db_title, db_year = best_match
            logger.debug(
                f"Fuzzy match: '{title}' → '{db_title}' "
                f"(score: {best_score:.1f}%, id: {movie_id})"
            )
            return best_match

        logger.debug(
            f"No fuzzy match found for '{title}' (best score: {best_score:.1f}%)"
        )
        return None

    def add_movie(self, movie_id: int, title: str, year: int | None) -> None:
        """
        Add a newly created movie to the cache.

        Args:
            movie_id: Database movie ID
            title: Movie title
            year: Release year
        """
        self._movies[movie_id] = {
            "title": title,
            "year": year,
        }
        logger.debug(f"Added to cache: {title} (id: {movie_id})")

    def __len__(self) -> int:
        """Return number of movies in cache."""
        return len(self._movies)
