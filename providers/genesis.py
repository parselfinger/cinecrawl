"""Genesis Deluxe Cinemas providers for all locations."""

from abc import abstractmethod
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from logging_config import get_logger
from models import Showtime
from movie_cache import get_global_cache
from providers.base import BaseProvider
from retry import async_retry

logger = get_logger(__name__)


def _parse_time(time_text: str, date_obj: datetime) -> datetime | None:
    """Parse time string and combine with date to create datetime object."""
    cleaned = time_text.strip().replace(" ", "")
    cleaned = cleaned.replace(".", "")

    try:
        parsed_time = datetime.strptime(cleaned, "%H:%M").time()
        return datetime.combine(date_obj.date(), parsed_time)
    except ValueError:
        pass

    cleaned_lower = cleaned.lower()
    try:
        parsed_time = datetime.strptime(cleaned_lower, "%I:%M%p").time()
        return datetime.combine(date_obj.date(), parsed_time)
    except ValueError:
        pass

    try:
        parsed_time = datetime.strptime(cleaned_lower, "%I%p").time()
        return datetime.combine(date_obj.date(), parsed_time)
    except ValueError:
        return None


@async_retry(max_attempts=3, backoff_factor=2.0)
async def _fetch_genesis_showtimes(
    cinema_name: str, location_name: str, cinema_id: str
) -> list[Showtime]:
    """
    Fetch Genesis Cinemas showtimes for a specific location.

    Args:
        cinema_name: Name of the cinema
        location_name: Location description
        cinema_id: Genesis cinema ID

    Returns:
        List of Showtime objects
    """
    url = "https://genesiscinemas.com/wp-admin/admin-ajax.php"

    showtimes = []
    seen = set()
    year_cache = {}  # Cache movie years to avoid duplicate detail page fetches
    today = datetime.now()

    for day_offset in range(5):
        target_date = today + timedelta(days=day_offset)
        date_str = target_date.strftime("%Y-%m-%d")

        payload = {
            "action": "jacro_filter_result",
            "film_date": date_str,
            "film_type": "Now Showing",
            "cinema_id": cinema_id,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=payload)
            response.raise_for_status()

            json_data = response.json()
            html_content = json_data.get("html", "")

            if not html_content:
                continue

            soup = BeautifulSoup(html_content, "html.parser")

        movie_containers = soup.find_all("div", class_="movie-tabs")

        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=True
        ) as detail_client:
            for container in movie_containers:
                title_elem = container.find("h3", class_="no-underline")
                if not title_elem:
                    continue
                title_link = title_elem.find("a")
                if title_link:
                    title = " ".join(title_link.get_text().split())
                else:
                    title = None
                if not title:
                    continue

                movie_url = title_link.get("href")

                year = None

                global_cache = get_global_cache()
                if global_cache:
                    match = global_cache.find_match(title, None)
                    if match:
                        _, _, cached_year = match
                        year = cached_year
                        logger.debug(
                            f"Global cache hit for '{title}': year={cached_year}"
                        )

                if year is None:
                    cache_key = title.lower().strip()
                    if cache_key in year_cache:
                        year = year_cache[cache_key]
                        logger.debug(f"Session cache hit for '{title}': year={year}")

                if year is None:
                    synopsis_link = container.find("a", id="tempsynoplink")
                    if synopsis_link:
                        detail_url = synopsis_link.get("href")
                    elif title_link:
                        detail_url = title_link.get("href")
                    else:
                        detail_url = None

                    if detail_url:
                        try:
                            detail_response = await detail_client.get(detail_url)
                            detail_response.raise_for_status()
                            detail_soup = BeautifulSoup(
                                detail_response.text, "html.parser"
                            )

                            movie_info = detail_soup.find("ul", class_="movie-info")
                            if movie_info:
                                for li in movie_info.find_all("li"):
                                    text = li.get_text(strip=True)
                                    if text.startswith("Released"):
                                        # Extract date from "Released 2025-12-12"
                                        date_str = text.replace("Released", "").strip()
                                        try:
                                            parsed_date = datetime.strptime(
                                                date_str, "%Y-%m-%d"
                                            )
                                            year = parsed_date.year
                                            logger.debug(
                                                f"Extracted year {year} from detail "
                                                f"page for '{title}'"
                                            )
                                            break
                                        except ValueError:
                                            logger.warning(
                                                f"Could not parse release date "
                                                f"'{date_str}' for '{title}'"
                                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to fetch detail page for '{title}': {e}"
                            )

                    if year is None:
                        logger.warning(f"Skipping '{title}': no release year found")
                        continue

                    # Cache the year for this movie in session cache
                    year_cache[cache_key] = year

                # Final check - skip if still no year
                if year is None:
                    logger.warning(f"Skipping '{title}': no release year found")
                    continue

                showtime_list = container.find("div", class_="jacro-showtime-list")
                if not showtime_list:
                    continue

                neworderpf = showtime_list.find("div", class_="neworderpf")
                if not neworderpf:
                    continue

                perf_buttons = neworderpf.find_all(
                    "a", class_=lambda x: x and "perfbtn" in x
                )

                for button in perf_buttons:
                    time_text = button.get_text(strip=True)
                    if time_text:
                        showtime_dt = _parse_time(time_text, target_date)
                        if not showtime_dt:
                            continue

                        key = (title, showtime_dt)
                        if key not in seen:
                            seen.add(key)
                            showtimes.append(
                                Showtime(
                                    cinema=cinema_name,
                                    location=location_name,
                                    title=title,
                                    time=time_text,
                                    date=showtime_dt,
                                    movie_url=movie_url,
                                    year=year,
                                )
                            )

    return showtimes


class GenesisProvider(BaseProvider):
    """Base class for all Genesis Deluxe Cinemas providers."""

    @property
    @abstractmethod
    def cinema_id(self) -> str:
        """Genesis cinema ID."""
        pass

    async def fetch(self) -> list[Showtime]:
        """Fetch showtimes for this Genesis location."""
        return await _fetch_genesis_showtimes(
            cinema_name=self.cinema_name,
            location_name=self.location,
            cinema_id=self.cinema_id,
        )


class GenesisMarylandProvider(GenesisProvider):
    """Provider for Genesis Deluxe Cinemas Maryland."""

    cinema_name = "Genesis Deluxe Cinemas"
    location = "Maryland Mall, Maryland, Lagos"
    cinema_id = "7"


class GenesisFestacProvider(GenesisProvider):
    """Provider for Genesis Deluxe Cinemas Festac."""

    cinema_name = "Genesis Deluxe Cinemas"
    location = "Festac Mall, Festac, Lagos"
    cinema_id = "5"


class GenesisLekkiProvider(GenesisProvider):
    """Provider for Genesis Deluxe Cinemas Lekki."""

    cinema_name = "Genesis Deluxe Cinemas"
    location = "Purple Mall, Lekki, Lagos"
    cinema_id = "11"
