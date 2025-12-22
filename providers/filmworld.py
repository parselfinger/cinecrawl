"""Filmworld Cinemas provider."""

import httpx
from bs4 import BeautifulSoup

from models import Showtime
from providers.base import BaseProvider
from retry import async_retry


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
                if head:
                    day_divs = head.find_all("div")
                    date = (
                        day_divs[1].get_text(strip=True) if len(day_divs) > 1 else None
                    )

                times_div = cell.find("div", class_="amy-intro-times")
                if times_div:
                    time_elements = times_div.find_all("div", recursive=False)
                    for time_elem in time_elements:
                        time_text = time_elem.get_text(strip=True)
                        if time_text and ":" in time_text:
                            showtimes.append(
                                Showtime(
                                    cinema=self.cinema_name,
                                    location=self.location,
                                    title=title,
                                    date=date,
                                    time=time_text,
                                )
                            )

        return showtimes
