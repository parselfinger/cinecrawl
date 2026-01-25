"""Grand Cinemas provider."""

import re
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from logging_config import get_logger
from models import Showtime
from providers.base import BaseProvider
from retry import async_retry

logger = get_logger(__name__)

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


class GrandCinemasProvider(BaseProvider):
    """Provider for Grand Cinemas."""

    cinema_name = "Grand Cinemas"
    location = "Lekki"

    @async_retry(max_attempts=3, backoff_factor=2.0)
    async def fetch(self) -> list[Showtime]:
        """Fetch Grand Cinemas showtimes."""
        url = "https://grandcinemas.com.ng/"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

        showtimes = []
        seen = set()
        year_cache = {}  # Cache movie years to avoid duplicate detail page fetches

        today = datetime.now()

        movie_tabs = soup.find_all("div", class_="movie-tabs")

        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=True
        ) as detail_client:
            for tab in movie_tabs:
                title_elem = tab.find("h3", class_="no-underline")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                synopsis_link = tab.find("a", class_="arrow-button")
                detail_url = synopsis_link.get("href")

                cache_key = title.lower().strip()
                if cache_key in year_cache:
                    year = year_cache[cache_key]
                    logger.debug(f"Cache hit for '{title}': year={year}")
                else:
                    year = None
                    if detail_url:
                        try:
                            detail_response = await detail_client.get(detail_url)
                            detail_response.raise_for_status()
                            detail_soup = BeautifulSoup(
                                detail_response.text, "html.parser"
                            )

                            movie_info = detail_soup.find("ul", class_="movie-info")
                            if movie_info:
                                for li in movie_info.find_all("li"):
                                    text = li.get_text(strip=True)
                                    if text.startswith("Released"):
                                        # Extract date from various formats:
                                        # "Released 2025-12-12"
                                        # "Released January 23, 2026"
                                        # "Released December 19th, 2025"
                                        date_str = text.replace("Released", "").strip()

                                        # Remove ordinal suffixes (st, nd, rd, th)
                                        date_str_cleaned = re.sub(
                                            r"(\d+)(st|nd|rd|th)", r"\1", date_str
                                        )

                                        # Try multiple date formats
                                        formats = [
                                            "%Y-%m-%d",  # 2025-12-12
                                            "%B %d, %Y",  # January 23, 2026
                                            "%b %d, %Y",  # Jan 23, 2026
                                        ]

                                        parsed = False
                                        for fmt in formats:
                                            try:
                                                parsed_date = datetime.strptime(
                                                    date_str_cleaned, fmt
                                                )
                                                year = parsed_date.year
                                                logger.debug(
                                                    f"Extracted year {year} from"
                                                    f"detail page for '{title}'"
                                                )
                                                parsed = True
                                                break
                                            except ValueError:
                                                continue

                                        if parsed:
                                            break
                                        else:
                                            logger.warning(
                                                f"Could not parse release date "
                                                f"'{date_str}' for '{title}'"
                                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to fetch detail page for '{title}': {e}"
                            )

                    if year is None:
                        logger.warning(f"Skipping '{title}': no release year found")
                        continue

                    # Cache the year for this movie
                    year_cache[cache_key] = year

                current_weekday = today.weekday()

                for day_index, day_abbr in DAY_MAP.items():
                    if day_index < current_weekday:
                        continue

                    day_class = f"{day_abbr}-time"
                    day_divs = tab.find_all("div", class_=day_class)

                    if not day_divs:
                        continue

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
                                        cinema=self.cinema_name,
                                        location=self.location,
                                        title=title,
                                        time=time_text,
                                        date=showtime_dt,
                                        year=year,
                                        movie_url=detail_url,
                                    )
                                )

        return showtimes
