from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from models import Showtime


async def scrape() -> list[Showtime]:
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

        movie_meta = back.find("ul", class_="movie-meta")
        times = []

        if movie_meta:
            for item in movie_meta.find_all("li"):
                text = item.get_text(strip=True)

                if "showing Time:" in text:
                    times_text = text.replace("showing Time:", "").strip()
                    times = [t.strip() for t in times_text.split(",")]

        for time in times:
            showtimes.append(
                Showtime(
                    cinema="Magnificent Cinemas",
                    location="Ikorodu Road, Lagos",
                    title=title,
                    time=time,
                    date=datetime.today().strftime("%B %d, %Y"),
                )
            )

    return showtimes
