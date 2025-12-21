import os

from dotenv import load_dotenv

from models import Showtime
from scrapers.utils import scrape_fusionintel_api

load_dotenv()


async def scrape() -> list[Showtime]:
    """
    Scrape EbonyLife Cinemas showtimes.

    Returns:
        List of Showtime objects.
    """
    bearer_token = os.getenv("EBONY_LIFE_TOKEN")
    if not bearer_token:
        raise ValueError("EBONY_LIFE_TOKEN environment variable not set")

    return await scrape_fusionintel_api(
        cinema_name="EbonyLife Cinemas",
        location_name="Victoria Island, Lagos",
        bearer_token=bearer_token,
        cinema_id=None,
        num_days=5,
    )
