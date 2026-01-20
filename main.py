"""Main scraper script with direct PostgreSQL access and TMDB normalization."""

import asyncio
import os

from dotenv import load_dotenv

from db import save_showtimes_to_db
from logging_config import get_logger, setup_logging
from models import CinemaResult
from movie_cache import MovieCache, set_global_cache
from providers.base import BaseProvider
from providers.bluepictures import BluePicturesProvider
from providers.ebonylife import EbonyLifeProvider
from providers.filmhouse import (
    FilmHouseCircleMallProvider,
    FilmHouseIkotaProvider,
    FilmHouseLandmarkProvider,
    FilmHouseLekkiIMAXProvider,
    FilmHouseOniruProvider,
    FilmHousePalmsLekkiProvider,
    FilmHouseSurulereProvider,
)
from providers.filmworld import FilmworldProvider
from providers.genesis import (
    GenesisFestacProvider,
    GenesisLekkiProvider,
    GenesisMarylandProvider,
)
from providers.magnificent import MagnificentProvider
from providers.ozonecinemas import OzoneCinemasProvider
from providers.silverbird import SilverbirdGalleriaProvider, SilverbirdIkejaProvider
from providers.skycinemas import SkyCinemasProvider
from providers.thccinema import THCCinemaProvider
from providers.viva import VivaIkejaProvider, VivaLekkiProvider
from validation import deduplicate_showtimes, validate_showtimes

# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logging()
logger = get_logger(__name__)


PROVIDERS: list[BaseProvider] = [
    # FusionIntel API providers
    EbonyLifeProvider(),
    SkyCinemasProvider(),
    OzoneCinemasProvider(),
    THCCinemaProvider(),
    VivaIkejaProvider(),
    VivaLekkiProvider(),
    # FilmHouse API providers
    FilmHouseLandmarkProvider(),
    FilmHouseLekkiIMAXProvider(),
    FilmHouseOniruProvider(),
    FilmHousePalmsLekkiProvider(),
    FilmHouseSurulereProvider(),
    FilmHouseCircleMallProvider(),
    FilmHouseIkotaProvider(),
    # HTML-based providers
    BluePicturesProvider(),
    FilmworldProvider(),
    GenesisMarylandProvider(),
    GenesisFestacProvider(),
    GenesisLekkiProvider(),
    # GrandCinemasProvider(),
    MagnificentProvider(),
    SilverbirdIkejaProvider(),
    SilverbirdGalleriaProvider(),
]


async def fetch_from_provider(provider: BaseProvider) -> CinemaResult:
    logger.info(f"Fetching showtimes from {provider.display_name}")
    try:
        showtimes = await provider.fetch()
        logger.info(
            f"Successfully fetched {len(showtimes)} showtimes "
            f"from {provider.display_name}"
        )
        return CinemaResult(
            cinema=provider.display_name, success=True, showtimes=showtimes
        )
    except Exception as e:
        logger.error(
            f"Failed to fetch from {provider.display_name}: "
            f"{type(e).__name__}: {str(e)}"
        )
        return CinemaResult(
            cinema=provider.display_name, success=False, showtimes=[], error=str(e)
        )


async def fetch_all() -> list[CinemaResult]:
    tasks = [fetch_from_provider(provider) for provider in PROVIDERS]
    results = await asyncio.gather(*tasks)
    return results


async def main():
    logger.info(f"Starting fetch from {len(PROVIDERS)} providers")

    database_url = os.getenv("DATABASE_URL")
    cache = None
    if database_url:
        cache = MovieCache()
        cache.load_from_db(database_url)
        set_global_cache(cache)  # Make cache accessible to providers
        logger.info(f"Movie cache loaded with {len(cache)} movies")

    results = await fetch_all()

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    all_showtimes = []
    for result in results:
        if result.success:
            all_showtimes.extend(result.showtimes)

    # Validate and deduplicate showtimes
    logger.info(f"Validating {len(all_showtimes)} showtimes")
    valid_showtimes = validate_showtimes(all_showtimes)
    unique_showtimes = deduplicate_showtimes(valid_showtimes)

    # Save to database
    if database_url:
        logger.info("Saving to database with movie normalization...")
        logger.info("Using IMDB Dev API for movie normalization")

        db_stats = save_showtimes_to_db(unique_showtimes, database_url, cache)

        logger.info(
            f"Database stats: {db_stats['inserted']} inserted, "
            f"{db_stats['deleted']} deleted, {db_stats['errors']} errors"
        )

    else:
        logger.warning("DATABASE_URL not set, skipping database save")

    logger.info(
        f"Completed: {len(successful)}/{len(PROVIDERS)} providers successful, "
        f"{len(unique_showtimes)} valid showtimes (from {len(all_showtimes)} total)"
    )

    if failed:
        logger.warning(f"{len(failed)} provider(s) failed:")
        for result in failed:
            logger.warning(f"  - {result.cinema}")

    return unique_showtimes


def lambda_handler(event, context):
    """
    AWS Lambda handler function.

    This function is called by AWS Lambda when triggered by EventBridge.
    """
    logger.info("Lambda function started")
    logger.info(f"Event: {event}")

    # Run the async main function
    showtimes = asyncio.run(main())

    return {
        "statusCode": 200,
        "body": {
            "message": "Scrape complete",
            "showtimes_count": len(showtimes),
        },
    }


if __name__ == "__main__":
    showtimes = asyncio.run(main())
