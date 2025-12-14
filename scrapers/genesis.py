from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from models import Showtime

LOCATIONS = {
    "maryland": {
        "cinema_id": "7",
        "cinema_name": "Genesis Deluxe Cinemas",
        "location": "Maryland Mall, Maryland, Lagos",
    },
    "festac": {
        "cinema_id": "5",
        "cinema_name": "Genesis Deluxe Cinemas",
        "location": "Festac Mall, Festac, Lagos",
    },
    "lekki": {
        "cinema_id": "11",
        "cinema_name": "Genesis Deluxe Cinemas",
        "location": "Purple Mall, Lekki, Lagos",
    },
}


def _parse_time(time_text: str, date_obj: datetime) -> datetime | None:
    """Parse time string and combine with date to create datetime object."""
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


async def scrape(location: str = "maryland") -> list[Showtime]:
    """
    Scrape Genesis Cinemas for a specific location.

    Args:
        location: The location to scrape. Must be one of: maryland, festac, lekki.
                 Defaults to 'maryland'.

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
    url = "https://genesiscinemas.com/wp-admin/admin-ajax.php"

    showtimes = []
    seen = set()
    today = datetime.now()

    for day_offset in range(5):
        target_date = today + timedelta(days=day_offset)
        date_str = target_date.strftime("%Y-%m-%d")

        payload = {
            "action": "jacro_filter_result",
            "film_date": date_str,
            "film_type": "Now Showing",
            "cinema_id": location_info["cinema_id"],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=payload)
            response.raise_for_status()

            json_data = response.json()
            html_content = json_data.get("html", "")

            if not html_content:
                continue

            soup = BeautifulSoup(html_content, "html.parser")

        movie_containers = soup.find_all("div", class_="movie-tabs")

        for container in movie_containers:
            title_elem = container.find("h3", class_="no-underline")
            if not title_elem:
                continue
            title_link = title_elem.find("a")
            if title_link:
                title = " ".join(title_link.get_text().split())
            else:
                title = None
            if not title:
                continue

            # Extract showtimes
            showtime_list = container.find("div", class_="jacro-showtime-list")
            if not showtime_list:
                continue

            # Find the main visible showtime container (neworderpf)
            # Avoid the hidden duplicates in innercatdived
            neworderpf = showtime_list.find("div", class_="neworderpf")
            if not neworderpf:
                continue

            # Find all performance buttons in the visible section only
            perf_buttons = neworderpf.find_all(
                "a", class_=lambda x: x and "perfbtn" in x
            )

            for button in perf_buttons:
                time_text = button.get_text(strip=True)
                if time_text:
                    showtime_dt = _parse_time(time_text, target_date)
                    if not showtime_dt:
                        continue

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
