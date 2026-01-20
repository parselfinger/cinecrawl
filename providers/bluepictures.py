"""Blue Pictures Cinemas provider."""

import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from logging_config import get_logger
from models import Showtime
from movie_cache import get_global_cache
from providers.base import BaseProvider
from providers.utils import parse_time_to_datetime
from retry import async_retry

logger = get_logger(__name__)


class BluePicturesProvider(BaseProvider):
    """Provider for Blue Pictures Cinemas."""

    cinema_name = "Blue Pictures Cinemas"
    location = "City Mall, Onikan, Lagos Island"

    @async_retry(max_attempts=3, backoff_factor=2.0)
    async def fetch(self) -> list[Showtime]:
        url = "https://bluepicturesng.com/now-showing/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/"
            "xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=30.0),
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
        except (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadTimeout,
            httpx.TimeoutException,
        ) as e:
            raise e

        showtimes = []

        movie_items = soup.find_all("div", class_="mb-movie-item")

        # Get global cache for fuzzy matching
        global_cache = get_global_cache()

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=30.0),
        ) as client:
            for item in movie_items:
                title_elem = item.find("h3", class_="movie-title")
                if not title_elem:
                    continue
                title = " ".join(title_elem.get_text().split())

                # Try to get year from global cache first (avoids HTTP request)
                year = None
                if global_cache:
                    match = global_cache.find_match(title, year=None)
                    if match:
                        _, _, year = match
                        logger.debug(f"Global cache hit for '{title}': year={year}")

                # If not in cache, fetch from detail page
                if year is None:
                    movie_link = item.find("a", href=True)
                    if not movie_link:
                        logger.warning(
                            f"Skipping '{title}': no movie detail link found"
                        )
                        continue

                    movie_url = movie_link["href"]
                    if not movie_url.startswith("http"):
                        movie_url = f"https://bluepicturesng.com{movie_url}"

                    try:
                        detail_response = await client.get(movie_url, headers=headers)
                        detail_response.raise_for_status()
                        detail_soup = BeautifulSoup(detail_response.text, "html.parser")

                        info_list = detail_soup.find("ul", class_="info-list")
                        if info_list:
                            for li in info_list.find_all("li", class_="item"):
                                title_elem = li.find("h4", class_="title")
                                if (
                                    title_elem
                                    and "Release Date:" in title_elem.get_text()
                                ):
                                    value_span = li.find("span", class_="value")
                                    if value_span:
                                        release_date_str = value_span.get_text(
                                            strip=True
                                        )
                                        for fmt in [
                                            "%B %d, %Y",
                                            "%b %d, %Y",
                                            "%Y-%m-%d",
                                        ]:
                                            try:
                                                parsed_date = datetime.strptime(
                                                    release_date_str, fmt
                                                )
                                                year = parsed_date.year
                                                logger.debug(
                                                    f"Extracted year {year} for "
                                                    f"'{title}'"
                                                )
                                                break
                                            except ValueError:
                                                continue
                                        break

                    except Exception as e:
                        logger.warning(f"Failed to fetch details for '{title}': {e}")

                if year is None:
                    logger.warning(f"Skipping '{title}': no release date found")
                    continue

                running_time_span = item.find("span", class_="running-time")
                if not running_time_span:
                    continue

                showtime_text = running_time_span.get_text(strip=True)
                times = re.findall(r"\d{1,2}:\d{2}[ap]m", showtime_text, re.IGNORECASE)

                for time in times:
                    showtime_dt = parse_time_to_datetime(time)
                    if showtime_dt is None:
                        logger.warning(
                            f"Skipping showtime for {title}: failed to parse time "
                            f"'{time}'"
                        )
                        continue

                    showtimes.append(
                        Showtime(
                            cinema=self.cinema_name,
                            location=self.location,
                            title=title,
                            time=time,
                            date=showtime_dt,
                            year=year,
                        )
                    )

        return showtimes
