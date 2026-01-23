"""Shared utilities for cinema providers."""

from datetime import date, datetime, timedelta

import httpx

from logging_config import get_logger
from models import Showtime
from retry import async_retry

logger = get_logger(__name__)


def parse_time_to_datetime(
    time_str: str, date_obj: date | None = None
) -> datetime | None:
    """
    Parse a time string and combine with a date to create a datetime object.

    Args:
        time_str: Time string (e.g., "7:30pm", "10:00 AM", "14:30")
        date_obj: Date to combine with time. If None, uses today's date.

    Returns:
        datetime object or None if parsing fails

    Examples:
        >>> parse_time_to_datetime("7:30pm")
        datetime(2024, 1, 15, 19, 30)
        >>> parse_time_to_datetime("10:00 AM", date(2024, 1, 20))
        datetime(2024, 1, 20, 10, 0)
        >>> parse_time_to_datetime("3:20PPM")  # Handle typos
        datetime(2024, 1, 15, 15, 20)
    """
    if date_obj is None:
        date_obj = datetime.today().date()

    cleaned = time_str.strip().lower().replace(" ", "")
    cleaned = cleaned.replace(".", ":")

    # Fix common typos: "ppm" -> "pm", "aam" -> "am"
    cleaned = cleaned.replace("ppm", "pm")
    cleaned = cleaned.replace("aam", "am")

    formats = [
        "%I:%M%p",  # 7:30pm
        "%I%p",  # 7pm
        "%H:%M",  # 19:30 (24-hour)
    ]

    for fmt in formats:
        try:
            time_obj = datetime.strptime(cleaned, fmt).time()
            return datetime.combine(date_obj, time_obj)
        except ValueError:
            continue

    logger.warning(f"Failed to parse time string: {time_str}")
    return None


@async_retry(max_attempts=3, backoff_factor=2.0)
async def fetch_fusionintel_showtimes(
    cinema_name: str,
    location_name: str,
    bearer_token: str,
    base_movie_url: str,
    cinema_id: str | None = None,
    num_days: int = 5,
) -> list[Showtime]:
    """
    Fetch showtimes from FusionIntel API.

    Args:
        cinema_name: Name of the cinema (e.g., "Viva Cinemas", "EbonyLife Cinemas")
        location_name: Location description (e.g., "Ikeja, Lagos")
        bearer_token: Bearer token for API authorization
        cinema_id: Optional cinema ID parameter (required for some cinemas like Viva)
        base_movie_url: Base Movie URL
        num_days: Number of days to fetch showtimes for (default: 5)

    Returns:
        List of Showtime objects
    """
    url = "https://max-api-readonly.fusionintel.io/api/v1/Showtimes/get-film-showtimes"

    showtimes = []
    seen = set()
    today = datetime.now()

    for day_offset in range(num_days):
        target_date = today + timedelta(days=day_offset)
        date_str = target_date.strftime("%d %b %Y 12:00 AM")

        params = {"todayDate": date_str}
        if cinema_id:
            params["cinemaId"] = cinema_id

        headers = {
            "Authorization": f"Bearer {bearer_token}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            json_response = response.json()
            data = json_response.get("data", [])

            if not data:
                continue

            for film_data in data:
                film = film_data.get("film", {})
                film_showtimes = film_data.get("showtimes", [])

                title = film.get("name")
                if not title:
                    continue

                release_date = film.get("releaseDate")
                year = datetime.fromisoformat(release_date.replace("Z", "+00:00")).year
                film_id = film.get("id")
                movie_url = base_movie_url + film_id

                for showtime in film_showtimes:
                    start_time_str = showtime.get("startTime")
                    status = showtime.get("status")

                    if not start_time_str or status != "Open":
                        continue

                    # Parse ISO 8601 datetime (e.g., "2025-12-14T10:40:00Z")
                    try:
                        showtime_dt = datetime.fromisoformat(
                            start_time_str.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        continue

                    # Extract time in 24-hour format for display
                    time_text = showtime_dt.strftime("%H:%M")

                    # Deduplicate using (title, datetime) tuple
                    key = (title, showtime_dt)
                    if key not in seen:
                        seen.add(key)
                        showtimes.append(
                            Showtime(
                                cinema=cinema_name,
                                location=location_name,
                                title=title,
                                time=time_text,
                                date=showtime_dt,
                                movie_url=movie_url,
                                year=year,
                            )
                        )

    return showtimes
