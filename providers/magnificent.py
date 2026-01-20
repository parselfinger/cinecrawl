"""Magnificent Cinemas provider."""

from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from logging_config import get_logger
from models import Showtime
from providers.base import BaseProvider
from providers.utils import parse_time_to_datetime
from retry import async_retry

logger = get_logger(__name__)


class MagnificentProvider(BaseProvider):
    cinema_name = "Magnificent Cinemas"
    location = "Ikorodu Road, Lagos"

    @async_retry(max_attempts=3, backoff_factor=2.0)
    async def fetch(self) -> list[Showtime]:
        url = "https://magnificentcinemas.com/"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

        showtimes = []
        movie_cards = soup.find_all("div", class_="info-card")

        for card in movie_cards:
            back = card.find("div", class_="back")
            if not back:
                continue

            # Extract title
            title_elem = back.find("h2")
            title = title_elem.get_text(strip=True) if title_elem else None
            if not title:
                continue

            year = datetime.now().year

            movie_meta = back.find("ul", class_="movie-meta")
            times = []

            if movie_meta:
                for item in movie_meta.find_all("li"):
                    text = item.get_text(strip=True)

                    if "showing Time:" in text:
                        times_text = text.replace("showing Time:", "").strip()
                        times = [t.strip() for t in times_text.split(",")]

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
                        year=year,
                    )
                )

        return showtimes
