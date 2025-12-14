import re
from datetime import date, datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from models import Showtime

DAY_NAME_TO_INDEX = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}

DAY_ALIASES = {
    "MONDAY": "MON",
    "TUES": "TUE",
    "TUESDAY": "TUE",
    "WEDNESDAY": "WED",
    "WEDS": "WED",
    "THUR": "THU",
    "THURS": "THU",
    "THURSDAY": "THU",
    "FRIDAY": "FRI",
    "SATURDAY": "SAT",
    "SUNDAY": "SUN",
}


def _normalize_day_token(token: str) -> str | None:
    cleaned = token.strip().upper()
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace(" ", "")
    if cleaned in DAY_ALIASES:
        cleaned = DAY_ALIASES[cleaned]
    elif cleaned.endswith("DAY") and len(cleaned) > 3:
        cleaned = cleaned[:-3]
    if len(cleaned) > 3:
        cleaned = cleaned[:3]
    return cleaned if cleaned in DAY_NAME_TO_INDEX else None


def _expand_day_range(day_range: str, reference: datetime) -> list[date]:
    tokens = day_range.strip().upper()
    if not tokens:
        return []
    # Handle cases like "FRI - SUN" by removing extra spaces
    tokens = tokens.replace("–", "-")  # en dash
    tokens = tokens.replace("—", "-")  # em dash
    tokens = re.sub(r"\s+", "", tokens)

    if "-" in tokens:
        start_token, end_token = tokens.split("-", 1)
        start_norm = _normalize_day_token(start_token)
        end_norm = _normalize_day_token(end_token)
        if start_norm is None or end_norm is None:
            return []
        start_idx = DAY_NAME_TO_INDEX[start_norm]
        end_idx = DAY_NAME_TO_INDEX[end_norm]

        day_indices = [start_idx]
        current = start_idx
        while current != end_idx:
            current = (current + 1) % 7
            day_indices.append(current)
            if len(day_indices) > 7:
                break
    else:
        single_norm = _normalize_day_token(tokens)
        if single_norm is None:
            return []
        day_indices = [DAY_NAME_TO_INDEX[single_norm]]

    if not day_indices:
        return []

    reference_date = reference.date()
    reference_weekday = reference_date.weekday()
    start_delta = (day_indices[0] - reference_weekday) % 7
    start_date = reference_date + timedelta(days=start_delta)

    return [start_date + timedelta(days=offset) for offset in range(len(day_indices))]


def _combine_datetime(date_obj: date, time_text: str) -> datetime:
    cleaned = time_text.strip().lower().replace(" ", "")
    cleaned = cleaned.replace(".", "")
    try:
        parsed_time = datetime.strptime(cleaned, "%I:%M%p").time()
    except ValueError:
        try:
            parsed_time = datetime.strptime(cleaned, "%I%p").time()
        except ValueError:
            return datetime.combine(date_obj, datetime.min.time())
    return datetime.combine(date_obj, parsed_time)


LOCATIONS = {
    "ikeja": {
        "url_slug": "ikeja",
        "cinema_name": "Silverbird Ikeja",
        "location": "Ikeja, Lagos",
    },
    "galleria": {
        "url_slug": "galleria",
        "cinema_name": "Silverbird Galleria",
        "location": "Victoria Island, Lagos",
    },
}


async def scrape(location: str = "ikeja") -> list[Showtime]:
    """
    Scrape showtimes for a specific Silverbird cinema location.

    Args:
        location: The location to scrape. Must be one of: ikeja, galleria.
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
    url = f"https://silverbirdcinemas.com/cinema/{location_info['url_slug']}/"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

    showtimes = []

    movie_articles = soup.find_all("article", class_="entry-item")

    now = datetime.now()

    for article in movie_articles:
        title_elem = article.find("h4", class_="entry-title")
        if not title_elem:
            continue
        title_link = title_elem.find("a")
        if title_link:
            title = " ".join(title_link.get_text().split())
        else:
            title = None
        if not title:
            continue

        showtime_elem = article.find("p", class_="cinema_page_showtime")
        if not showtime_elem:
            continue

        showtime_text = showtime_elem.get_text()

        # Extract day ranges and their times
        # Format: "FRI-SUN: times" or "MON-THUR: times"
        parts = showtime_text.split("Showtime:")[-1].strip()

        day_patterns = re.findall(
            r"([A-Z\-]+):\s*([^A-Z]+?)(?=[A-Z\-]+:|$)", parts, re.DOTALL
        )

        for day_range, times_text in day_patterns:
            if "to be updated" in times_text.lower() or "tba" in times_text.lower():
                continue

            expanded_dates = _expand_day_range(day_range, now)
            if not expanded_dates:
                continue

            # Extract individual times
            times = re.findall(r"\d{1,2}:\d{2}\s*[ap]m", times_text, re.IGNORECASE)

            if not times:
                continue

            for expanded_date in expanded_dates:
                for time in times:
                    start_at = _combine_datetime(expanded_date, time)
                    showtimes.append(
                        Showtime(
                            cinema=location_info["cinema_name"],
                            location=location_info["location"],
                            title=title,
                            time=time,
                            date=start_at,
                        )
                    )

    return showtimes
