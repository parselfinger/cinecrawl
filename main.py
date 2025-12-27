import asyncio
import json
from dataclasses import asdict
from datetime import datetime

from dotenv import load_dotenv

from logging_config import get_logger, setup_logging
from models import CinemaResult
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
from providers.grandcinemas import GrandCinemasProvider
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
    GrandCinemasProvider(),
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
    results = await fetch_all()

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    all_showtimes = []
    for result in results:
        if result.success:
            all_showtimes.extend(result.showtimes)

    logger.info(f"Validating {len(all_showtimes)} showtimes")
    valid_showtimes = validate_showtimes(all_showtimes)
    unique_showtimes = deduplicate_showtimes(valid_showtimes)

    def serialize_showtime(showtime):
        data = asdict(showtime)
        if isinstance(data.get("date"), datetime):
            data["date"] = data["date"].isoformat()
        return data

    with open("showtimes.json", "w") as f:
        json.dump([serialize_showtime(s) for s in unique_showtimes], f, indent=2)

    logger.info(
        f"Completed: {len(successful)}/{len(PROVIDERS)} providers successful, "
        f"{len(unique_showtimes)} valid showtimes (from {len(all_showtimes)} total)"
    )
    logger.info("Saved to showtimes.json")

    if failed:
        logger.warning(f"{len(failed)} provider(s) failed:")
        for result in failed:
            logger.warning(f"  - {result.cinema}")

    return unique_showtimes


if __name__ == "__main__":
    showtimes = asyncio.run(main())
