"""Filmworld Cinemas provider."""

from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from logging_config import get_logger
from models import Showtime
from providers.base import BaseProvider
from providers.utils import parse_time_to_datetime
from retry import async_retry

logger = get_logger(__name__)


class FilmworldProvider(BaseProvider):
    """Provider for Filmworld Cinemas."""

    cinema_name = "Filmworld Cinemas"
    location = "Idimu, Lagos"

    @async_retry(max_attempts=3, backoff_factor=2.0)
    async def fetch(self) -> list[Showtime]:
        url = "https://filmworldcinemas.com/showtime/daily-showtime/"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

        showtimes = []
        movie_items = soup.find_all("div", class_="amy-movie-item")

        for item in movie_items:
            title_elem = item.find("h3", class_="amy-movie-field-title")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)

            # Extract times
            date_cells = item.find_all("div", class_="amy-cell")
            for cell in date_cells:
                head = cell.find("div", class_="amy-head")
                date_str = None
                if head:
                    day_divs = head.find_all("div")
                    date_str = (
                        day_divs[1].get_text(strip=True) if len(day_divs) > 1 else None
                    )

                times_div = cell.find("div", class_="amy-intro-times")
                if times_div:
                    time_elements = times_div.find_all("div", recursive=False)
                    for time_elem in time_elements:
                        time_text = time_elem.get_text(strip=True)
                        if not time_text or ":" not in time_text:
                            continue

                        # Parse date string if available, otherwise use today
                        date_obj = None
                        if date_str:
                            try:
                                # Try common date formats
                                for fmt in ["%b %d", "%B %d", "%d %b", "%d %B"]:
                                    try:
                                        parsed = datetime.strptime(date_str, fmt)
                                        # Add current year
                                        date_obj = parsed.replace(
                                            year=datetime.now().year
                                        ).date()
                                        break
                                    except ValueError:
                                        continue
                            except Exception as e:
                                logger.warning(
                                    f"Failed to parse date '{date_str}': {e}"
                                )

                        showtime_dt = parse_time_to_datetime(time_text, date_obj)
                        if showtime_dt is None:
                            logger.warning(
                                f"Skipping showtime for {title}: "
                                f"failed to parse time '{time_text}'"
                            )
                            continue

                        showtimes.append(
                            Showtime(
                                cinema=self.cinema_name,
                                location=self.location,
                                title=title,
                                date=showtime_dt,
                                time=time_text,
                            )
                        )

        return showtimes
