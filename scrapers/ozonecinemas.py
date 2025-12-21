import os

from dotenv import load_dotenv

from models import Showtime
from scrapers.utils import scrape_fusionintel_api

load_dotenv()


async def scrape() -> list[Showtime]:
    """
    Scrape Ozone Cinemas showtimes.

    Returns:
        List of Showtime objects.
    """
    bearer_token = os.getenv("OZONE_CINEMAS_TOKEN")
    if not bearer_token:
        raise ValueError("OZONE_CINEMAS_TOKEN environment variable not set")

    return await scrape_fusionintel_api(
        cinema_name="Ozone Cinemas",
        location_name="Yaba, Lagos",
        bearer_token=bearer_token,
        cinema_id="ozo-a4239533",
        num_days=5,
    )
