import os
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

from models import Showtime

load_dotenv()

LOCATIONS = {
    "ikeja": {
        "cinema_id": "viv-27fd41dc",
        "cinema_name": "Viva Cinemas",
        "location": "Ikeja, Lagos",
    },
    "lekki": {
        "cinema_id": "viv-6ac91519",
        "cinema_name": "Viva Cinemas",
        "location": "Lekki, Lagos",
    },
}


def _parse_time(time_text: str, date_obj: datetime) -> datetime | None:
    cleaned = time_text.strip().replace(" ", "")
    cleaned = cleaned.replace(".", "")

    try:
        parsed_time = datetime.strptime(cleaned, "%H:%M").time()
        return datetime.combine(date_obj.date(), parsed_time)
    except ValueError:
        pass

    cleaned_lower = cleaned.lower()
    try:
        parsed_time = datetime.strptime(cleaned_lower, "%I:%M%p").time()
        return datetime.combine(date_obj.date(), parsed_time)
    except ValueError:
        pass

    try:
        parsed_time = datetime.strptime(cleaned_lower, "%I%p").time()
        return datetime.combine(date_obj.date(), parsed_time)
    except ValueError:
        return None


async def scrape(location: str = "ikeja") -> list[Showtime]:
    """
    Scrape Viva Cinemas for a specific location.

    Args:
        location: The location to scrape. Must be one of: ikeja, lekki.
                 Defaults to 'ikeja'.

    Returns:
        List of Showtime objects for the specified location.
    """
    location = location.lower()
    if location not in LOCATIONS:
        raise ValueError(
            f"Unsupported location: {location}. "
            f"Supported locations: {', '.join(LOCATIONS.keys())}"
        )

    location_info = LOCATIONS[location]
    cinema_id = location_info["cinema_id"]

    # Get bearer token from environment variable
    bearer_token = os.getenv("VIVA_CINEMAS_TOKEN")
    if not bearer_token:
        raise ValueError("VIVA_CINEMAS_TOKEN environment variable not set ")

    url = "https://max-api-readonly.fusionintel.io/api/v1/Showtimes/get-film-showtimes"

    showtimes = []
    seen = set()
    today = datetime.now()

    for day_offset in range(5):
        target_date = today + timedelta(days=day_offset)
        date_str = target_date.strftime("%d %b %Y 12:00 AM")

        params = {
            "todayDate": date_str,
            "cinemaId": cinema_id,
        }

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
                                cinema=location_info["cinema_name"],
                                location=location_info["location"],
                                title=title,
                                time=time_text,
                                date=showtime_dt,
                            )
                        )

    return showtimes
