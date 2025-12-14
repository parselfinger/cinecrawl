from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from models import Showtime

DAY_MAP = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}


def _parse_time(time_text: str, date_obj: datetime) -> datetime | None:
    cleaned = time_text.strip().lower().replace(" ", "")
    cleaned = cleaned.replace(".", "")
    try:
        parsed_time = datetime.strptime(cleaned, "%I:%M%p").time()
    except ValueError:
        try:
            parsed_time = datetime.strptime(cleaned, "%I%p").time()
        except ValueError:
            return None
    return datetime.combine(date_obj.date(), parsed_time)


async def scrape() -> list[Showtime]:
    """
    Scrape Grand Cinemas - Jabi Lake Mall, Abuja

    Returns:
        List of Showtime objects
    """
    url = "https://grandcinemas.com.ng/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

    showtimes = []
    seen = set()  # Track (title, datetime) to avoid duplicates

    today = datetime.now()

    movie_tabs = soup.find_all("div", class_="movie-tabs")

    for tab in movie_tabs:
        title_elem = tab.find("h3", class_="no-underline")
        if not title_elem:
            continue
        title = " ".join(title_elem.get_text().split())

        current_weekday = today.weekday()

        for day_index, day_abbr in DAY_MAP.items():
            if day_index < current_weekday:
                continue

            day_class = f"{day_abbr}-time"
            day_divs = tab.find_all("div", class_=day_class)

            if not day_divs:
                continue

            # Calculate the date for this day (0 = today, 1 = tomorrow, etc.)
            days_ahead = day_index - current_weekday
            target_date = today + timedelta(days=days_ahead)

            day_div = day_divs[0]
            time_spans = day_div.find_all("span", class_="time")

            for time_span in time_spans:
                time_text = " ".join(time_span.get_text().split())
                if time_text:
                    showtime_dt = _parse_time(time_text, target_date)
                    if not showtime_dt:
                        continue

                    key = (title, showtime_dt)
                    if key not in seen:
                        seen.add(key)
                        showtimes.append(
                            Showtime(
                                cinema="Grand Cinemas",
                                location="Jabi Lake Mall, Abuja",
                                title=title,
                                time=time_text,
                                date=showtime_dt,
                            )
                        )

    return showtimes
