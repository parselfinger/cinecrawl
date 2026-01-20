from datetime import datetime, timedelta

import psycopg2

from logging_config import get_logger
from models import Showtime as ShowtimeDataclass
from movie_normalizer import get_normalized_movie

logger = get_logger(__name__)


def get_connection(database_url: str):
    return psycopg2.connect(database_url)


def get_or_create_movie(conn, title: str, year: int, cache=None) -> int:
    """
    Get existing movie by title or create new one with IMDB data.

    Optimization: Uses in-memory cache with fuzzy matching before hitting database.

    Flow:
    1. Check in-memory cache with fuzzy matching (85% similarity)
    2. If not found, normalize via IMDB API (which uses session cache)
    3. Insert new movie and add to cache

    Args:
        conn: psycopg2 connection
        title: Movie title from scraper
        year: Release year (required for better API matching)
        cache: Optional MovieCache instance for fuzzy matching

    Returns:
        Movie ID
    """
    if cache:
        match = cache.find_match(title, year)
        if match:
            movie_id, db_title, db_year = match
            logger.debug(f"Cache hit: '{title}' → '{db_title}' (id={movie_id})")
            return movie_id

    # Not in cache - normalize using IMDB API (uses session cache)
    movie_data = get_normalized_movie(title, year)
    normalized_title = movie_data["title"]

    # Check if normalized title already exists in DB
    # (handles case where scraper gives different title but API normalizes to same)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM movies WHERE title = %s LIMIT 1", (normalized_title,)
        )
        result = cur.fetchone()
        if result:
            movie_id = result[0]
            logger.debug(
                f"Found existing movie after normalization:"
                f" '{title}' → '{normalized_title}' (id={movie_id})"
            )
            # Add to cache for future lookups
            if cache:
                cache.add_movie(
                    movie_id, normalized_title, movie_data.get("release_year")
                )
            return movie_id

        # Create new movie
        cur.execute(
            """
            INSERT INTO movies (title, description, release_year, duration_minutes,
            rating, poster_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                normalized_title,
                movie_data.get("description"),
                movie_data.get("release_year"),
                movie_data.get("duration_minutes"),
                movie_data.get("rating"),
                movie_data.get("poster_url"),
            ),
        )

        movie_id = cur.fetchone()[0]
        conn.commit()

        source = movie_data.get("source", "unknown")
        logger.info(
            f"Created movie from {source.upper()}: {normalized_title} (id={movie_id})"
        )

        # Add to cache for future lookups
        if cache:
            cache.add_movie(movie_id, normalized_title, movie_data.get("release_year"))

        return movie_id


def get_or_create_cinema(conn, name: str, location: str) -> int:
    """
    Get existing cinema by name and location or create new one.

    Args:
        conn: psycopg2 connection
        name: Cinema name
        location: Cinema location

    Returns:
        Cinema ID
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM cinemas WHERE name = %s AND location = %s LIMIT 1",
            (name, location),
        )

        result = cur.fetchone()
        if result:
            cinema_id = result[0]
            logger.debug(
                f"Found existing cinema: {name} at {location} (id={cinema_id})"
            )
            return cinema_id

        cur.execute(
            """
            INSERT INTO cinemas (name, location)
            VALUES (%s, %s)
            RETURNING id
            """,
            (name, location),
        )

        cinema_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Created cinema: {name} at {location} (id={cinema_id})")
        return cinema_id


def save_showtimes_to_db(
    showtimes: list[ShowtimeDataclass],
    database_url: str,
    cache=None,
) -> dict:
    """
    Save showtimes to database using direct SQL.

    Args:
        showtimes: List of Showtime dataclass objects
        database_url: PostgreSQL connection string
        cache: Optional MovieCache instance for fuzzy matching

    Returns:
        Dict with stats: inserted, duplicates, errors
    """
    conn = get_connection(database_url)
    stats = {"inserted": 0, "duplicates": 0, "errors": 0}

    try:
        for showtime in showtimes:
            try:
                movie_id = get_or_create_movie(
                    conn, showtime.title, showtime.year, cache
                )

                cinema_id = get_or_create_cinema(
                    conn, showtime.cinema, showtime.location
                )

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO showtimes (movie_id, cinema_id, start_time,
                        screen_type)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (movie_id, cinema_id, showtime.date, showtime.screen_type),
                    )

                conn.commit()
                stats["inserted"] += 1

            except psycopg2.IntegrityError:
                conn.rollback()
                stats["duplicates"] += 1
                logger.debug(
                    f"Duplicate/constraint: {showtime.cinema} - "
                    f"{showtime.title} at {showtime.date}"
                )

            except Exception as e:
                conn.rollback()
                stats["errors"] += 1
                logger.error(
                    f"Error saving showtime: {type(e).__name__}: {e}\n"
                    f"  Cinema: {showtime.cinema}, Title: {showtime.title}"
                )

        logger.info(
            f"Database save complete: {stats['inserted']} inserted, "
            f"{stats['duplicates']} duplicates, {stats['errors']} errors"
        )

    finally:
        conn.close()

    return stats


def cleanup_old_showtimes(database_url: str, days_old: int = 1) -> int:
    conn = get_connection(database_url)
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM showtimes WHERE start_time < %s",
                (cutoff_date,),
            )
            deleted = cur.rowcount

        conn.commit()
        logger.info(f"Deleted {deleted} old showtimes (older than {days_old} days)")
        return deleted

    finally:
        conn.close()
