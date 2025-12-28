"""Blue Pictures Cinemas provider."""

import re

import httpx
from bs4 import BeautifulSoup

from logging_config import get_logger
from models import Showtime
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

        for item in movie_items:
            title_elem = item.find("h3", class_="movie-title")
            if not title_elem:
                continue
            title = " ".join(title_elem.get_text().split())

            running_time_span = item.find("span", class_="running-time")
            if not running_time_span:
                continue

            showtime_text = running_time_span.get_text(strip=True)
            times = re.findall(r"\d{1,2}:\d{2}[ap]m", showtime_text, re.IGNORECASE)

            for time in times:
                showtime_dt = parse_time_to_datetime(time)
                if showtime_dt is None:
                    logger.warning(
                        f"Skipping showtime for {title}: failed to parse time '{time}'"
                    )
                    continue

                showtimes.append(
                    Showtime(
                        cinema=self.cinema_name,
                        location=self.location,
                        title=title,
                        time=time,
                        date=showtime_dt,
                    )
                )

        return showtimes
