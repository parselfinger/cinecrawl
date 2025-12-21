import os

from dotenv import load_dotenv

from models import Showtime
from scrapers.utils import scrape_fusionintel_api

load_dotenv()

LOCATIONS = {
    "ikeja": {
        "cinema_id": "viv-27fd41dc",
        "cinema_name": "Viva Cinemas",
        "location": "Ikeja, Lagos",
    },
    "lekki": {
        "cinema_id": "viv-6ac91519",
        "cinema_name": "Viva Cinemas",
        "location": "Lekki, Lagos",
    },
}


async def scrape(location: str = "ikeja") -> list[Showtime]:
    """
    Scrape Viva Cinemas for a specific location.

    Args:
        location: The location to scrape. Must be one of: ikeja, lekki.
                 Defaults to 'ikeja'.

    Returns:
        List of Showtime objects for the specified location.
    """
    location = location.lower()
    if location not in LOCATIONS:
        raise ValueError(
            f"Unsupported location: {location}. "
            f"Supported locations: {', '.join(LOCATIONS.keys())}"
        )

    location_info = LOCATIONS[location]
    cinema_id = location_info["cinema_id"]

    # Get bearer token from environment variable
    bearer_token = os.getenv("VIVA_CINEMAS_TOKEN")
    if not bearer_token:
        raise ValueError("VIVA_CINEMAS_TOKEN environment variable not set")

    return await scrape_fusionintel_api(
        cinema_name=location_info["cinema_name"],
        location_name=location_info["location"],
        bearer_token=bearer_token,
        cinema_id=cinema_id,
        num_days=5,
    )
