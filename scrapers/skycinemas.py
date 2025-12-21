import os

from dotenv import load_dotenv

from models import Showtime
from scrapers.utils import scrape_fusionintel_api

load_dotenv()


async def scrape() -> list[Showtime]:
    """
    Scrape Sky Cinemas showtimes.

    Returns:
        List of Showtime objects.
    """
    bearer_token = os.getenv("SKY_CINEMAS_TOKEN")
    if not bearer_token:
        raise ValueError("SKY_CINEMAS_TOKEN environment variable not set")

    return await scrape_fusionintel_api(
        cinema_name="Sky Cinemas",
        location_name="Sangotedo, Lagos",
        bearer_token=bearer_token,
        cinema_id=None,
        num_days=5,
    )
