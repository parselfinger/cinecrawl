import asyncio
import json
from dataclasses import asdict
from datetime import datetime

from dotenv import load_dotenv

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

# Load environment variables from .env file
load_dotenv()


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
    """Fetch showtimes from a provider with error handling"""
    try:
        showtimes = await provider.fetch()
        return CinemaResult(
            cinema=provider.display_name, success=True, showtimes=showtimes
        )
    except Exception as e:
        return CinemaResult(
            cinema=provider.display_name, success=False, showtimes=[], error=str(e)
        )


async def fetch_all() -> list[CinemaResult]:
    tasks = [fetch_from_provider(provider) for provider in PROVIDERS]
    results = await asyncio.gather(*tasks)
    return results


async def main():
    results = await fetch_all()

    all_showtimes = []
    for result in results:
        if result.success:
            all_showtimes.extend(result.showtimes)
        else:
            print(f"Error fetching from {result.cinema}: {result.error}")

    def serialize_showtime(showtime):
        data = asdict(showtime)
        if isinstance(data.get("date"), datetime):
            data["date"] = data["date"].isoformat()
        return data

    with open("showtimes.json", "w") as f:
        json.dump([serialize_showtime(s) for s in all_showtimes], f, indent=2)

    print("Saved to showtimes.json\n")

    return all_showtimes


if __name__ == "__main__":
    showtimes = asyncio.run(main())
