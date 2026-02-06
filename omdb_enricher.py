import re
import time
from typing import Any

import psycopg2
import requests

from logging_config import get_logger

logger = get_logger(__name__)

OMDB_URL = "https://www.omdbapi.com/"


def _parse_rating_value(value_str: str | None) -> int | float | None:
    """Parse '5.7/10', '87%', '65/100' to numeric value."""
    if not value_str:
        return None
    match = re.search(r"([\d.]+)", str(value_str))
    if match:
        try:
            val = float(match.group(1))
            return int(val) if val == int(val) else val
        except ValueError:
            return None
    return None


def _parse_ratings(omdb_data: dict) -> dict[str, int | float | None]:
    result: dict[str, int | float | None] = {
        "imdb_rating": None,
        "rotten_tomatoes_rating": None,
        "metacritic_rating": None,
    }

    result["imdb_rating"] = _parse_rating(omdb_data.get("imdbRating"))

    metascore = omdb_data.get("Metascore")
    if metascore and metascore != "N/A":
        result["metacritic_rating"] = _parse_rating_value(metascore)

    for r in omdb_data.get("Ratings") or []:
        source = (r.get("Source") or r.get("source") or "").lower()
        value = r.get("Value") or r.get("value")
        parsed = _parse_rating_value(value)
        if not parsed:
            continue
        if "rotten" in source or "tomatoes" in source:
            result["rotten_tomatoes_rating"] = int(parsed)
        elif "metacritic" in source:
            result["metacritic_rating"] = int(parsed)
        elif "internet" in source or "imdb" in source:
            result["imdb_rating"] = parsed

    return result


def _parse_runtime(runtime_str: str | None) -> int | None:
    """Parse '88 min' or '1h 30min' to minutes."""
    if not runtime_str:
        return None
    match = re.search(r"(\d+)\s*min", runtime_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s*h", runtime_str, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 60
    return None


def _parse_rating(rating_str: str | None) -> float | None:
    """Parse '5.7' or '5.7/10' to float."""
    if not rating_str:
        return None
    match = re.search(r"([\d.]+)", str(rating_str))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def fetch_omdb_movie(imdb_id: str, api_key: str) -> dict[str, Any] | None:
    """
    Fetch movie details from OMDB API by IMDB ID.

    Args:
        imdb_id: IMDB ID (e.g. tt23572848)
        api_key: OMDB API key

    Returns:
        Dict with poster_url, description, rating, duration_minutes, release_year
        or None if not found / API error
    """
    try:
        response = requests.get(
            OMDB_URL,
            params={"apikey": api_key, "i": imdb_id},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("Response") != "True":
            err = data.get("Error", "Unknown")
            logger.debug(f"OMDB no result for {imdb_id}: {err}")
            return None

        ratings = _parse_ratings(data)
        return {
            "poster_url": data.get("Poster") or None,
            "description": data.get("Plot") or None,
            "rating": ratings.get("imdb_rating"),
            "rotten_tomatoes_rating": ratings.get("rotten_tomatoes_rating"),
            "metacritic_rating": ratings.get("metacritic_rating"),
            "duration_minutes": _parse_runtime(data.get("Runtime")),
            "release_year": (
                int(data["Year"])
                if data.get("Year") and data["Year"].isdigit()
                else None
            ),
        }

    except Exception as e:
        logger.warning(f"OMDB fetch failed for {imdb_id}: {type(e).__name__}: {e}")
        return None


def enrich_movies(database_url: str, api_key: str, delay_seconds: float = 0.5) -> dict:
    conn = psycopg2.connect(database_url)
    stats = {"enriched": 0, "skipped": 0, "errors": 0}

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, imdb_id, title, poster_url
                FROM movies
                WHERE imdb_id IS NOT NULL AND imdb_id != ''
                """
            )
            rows = cur.fetchall()

        for movie_id, imdb_id, title, current_poster_url in rows:
            omdb_data = fetch_omdb_movie(imdb_id, api_key)
            time.sleep(delay_seconds)

            if not omdb_data:
                stats["errors"] += 1
                continue

            # Only update non-null values from OMDB
            # Poster: only update if currently null (preserve existing)
            updates = []
            params = []

            if omdb_data.get("poster_url") and (
                current_poster_url is None or current_poster_url == ""
            ):
                updates.append("poster_url = %s")
                params.append(omdb_data["poster_url"])
            if omdb_data.get("description"):
                updates.append("description = %s")
                params.append(omdb_data["description"])
            if omdb_data.get("rating") is not None:
                updates.append("rating = %s")
                params.append(omdb_data["rating"])
            if omdb_data.get("duration_minutes") is not None:
                updates.append("duration_minutes = %s")
                params.append(omdb_data["duration_minutes"])
            if omdb_data.get("release_year") is not None:
                updates.append("release_year = %s")
                params.append(omdb_data["release_year"])
            if omdb_data.get("rotten_tomatoes_rating") is not None:
                updates.append("rotten_tomatoes_rating = %s")
                params.append(omdb_data["rotten_tomatoes_rating"])
            if omdb_data.get("metacritic_rating") is not None:
                updates.append("metacritic_rating = %s")
                params.append(omdb_data["metacritic_rating"])

            if not updates:
                stats["skipped"] += 1
                continue

            params.append(movie_id)
            sql = f"UPDATE movies SET {', '.join(updates)} WHERE id = %s"

            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                conn.commit()
                stats["enriched"] += 1
                logger.info(f"Enriched: {title} (id={movie_id})")
            except Exception as e:
                conn.rollback()
                stats["errors"] += 1
                logger.error(f"Failed to update {title}: {e}")

    finally:
        conn.close()

    return stats
