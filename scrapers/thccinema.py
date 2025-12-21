import os

from dotenv import load_dotenv

from models import Showtime
from scrapers.utils import scrape_fusionintel_api

load_dotenv()


async def scrape() -> list[Showtime]:
    """
    Scrape THC Cinema showtimes.

    Returns:
        List of Showtime objects.
    """
    bearer_token = os.getenv("THC_CINEMA_TOKEN")
    if not bearer_token:
        raise ValueError("THC_CINEMA_TOKEN environment variable not set")

    return await scrape_fusionintel_api(
        cinema_name="THC Cinema",
        location_name="Agege, Lagos",
        bearer_token=bearer_token,
        cinema_id=None,
        num_days=5,
    )
