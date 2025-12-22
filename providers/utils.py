"""Shared utilities for FusionIntel API-based cinema providers."""

from datetime import datetime, timedelta

import httpx

from models import Showtime


async def fetch_fusionintel_showtimes(
    cinema_name: str,
    location_name: str,
    bearer_token: str,
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
                            )
                        )

    return showtimes
