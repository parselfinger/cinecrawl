import asyncio
import json
from typing import List
from models import CinemaResult



SCRAPERS = [
]


async def scrape_cinema(name: str, scrape_func) -> CinemaResult:
    """Scrape a single cinema with error handling"""
    try:
        showtimes = await scrape_func()
        return CinemaResult(
            cinema=name,
            success=True,
            showtimes=showtimes
        )
    except Exception as e:
        return CinemaResult(
            cinema=name,
            success=False,
            showtimes=[],
            error=str(e)
        )


async def scrape_all() -> List[CinemaResult]:
    """Scrape all cinemas concurrently"""
    tasks = [scrape_cinema(name, func) for name, func in SCRAPERS]
    results = await asyncio.gather(*tasks)
    return results





async def main():
    """Main entry point"""
    results = await scrape_all()

    all_showtimes = []
    for result in results:
        if result.success:
            all_showtimes.extend(result.showtimes)

    with open('showtimes.json', 'w') as f:
        json.dump([vars(s) for s in all_showtimes], f, indent=2)

    print("Saved to showtimes.json\n")

    return all_showtimes


if __name__ == "__main__":
    showtimes = asyncio.run(main())