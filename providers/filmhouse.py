"""FilmHouse Cinemas providers for all locations."""

import hashlib
import hmac
import json
import os
import re
import time
from abc import abstractmethod
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

from exceptions import AuthenticationError
from logging_config import get_logger
from models import Showtime
from providers.base import BaseProvider
from retry import async_retry

load_dotenv()
logger = get_logger(__name__)


def generate_signature(body_dict: dict, secret_key: str, timestamp: int) -> str:
    """Generate FilmHouse API signature."""
    sorted_keys = sorted(body_dict.keys())
    sorted_body = {k: body_dict[k] for k in sorted_keys}

    json_str = json.dumps(sorted_body, separators=(",", ":"), ensure_ascii=False)

    special_chars = (
        r"[áéíóúüñ¿¡ÁÉÍÓÚÜÑāčēģīķļņšūžĀČĒĢĪĶĻŅŠŪŽ£€ğĞ"
        r"\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1\u00bf\u00a1"
        r"\u00c1\u00c9\u00cd\u00d3\u00da\u00dc\u00d1"
        r"\u0101\u010d\u0113\u0123\u012b\u0137\u013c\u0146\u0161\u016b\u017e"
        r"\u0100\u010c\u0112\u0122\u012a\u0136\u013b\u0145\u0160\u016a\u017d"
        r"\u00a3\u20ac\u011f\u011e]"
    )
    cleaned_json = re.sub(special_chars, "", json_str)

    hmac_key = secret_key + str(timestamp)

    signature = hmac.new(
        hmac_key.encode("utf-8"), cleaned_json.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return signature


class FilmHouseProvider(BaseProvider):
    """
    Base class for all FilmHouse Cinemas providers.

    Subclasses must define:
    - cinema_name: Name of the cinema (usually "FilmHouse Cinemas")
    - location: Location of the cinema
    - cinema_location_id: FilmHouse API location ID
    """

    @property
    @abstractmethod
    def cinema_name(self) -> str:
        """Name of the cinema."""
        pass

    @property
    @abstractmethod
    def location(self) -> str:
        """Location of the cinema."""
        pass

    @property
    @abstractmethod
    def cinema_location_id(self) -> str:
        """FilmHouse API cinema location ID."""
        pass

    @async_retry(max_attempts=3, backoff_factor=2.0)
    async def fetch(self) -> list[Showtime]:
        """
        Fetch showtimes from FilmHouse API.

        Returns:
            List of Showtime objects.

        Raises:
            AuthenticationError: If FILMHOUSE_SECRET_KEY not set.
        """
        secret_key = os.getenv("FILMHOUSE_SECRET_KEY")
        if not secret_key:
            raise AuthenticationError(
                self.display_name, "FILMHOUSE_SECRET_KEY environment variable not set"
            )

        url = "https://filmhouseng.api.cinesync.io/api_v3/cms_widget/index"

        showtimes = []
        seen = set()
        today = datetime.now()

        for day_offset in range(5):
            target_date = today + timedelta(days=day_offset)
            date_str = target_date.strftime("%Y-%m-%d")

            timestamp = int(time.time())

            body = {
                "sales_channel_id": 1,
                "cinema_location_id": self.cinema_location_id,
                "widget_id": "movie_calendar",
                "api": "list",
                "session_date": date_str,
                "has_limit": 0,
                "per_page": 100,
                "page_number": 1,
                "url_key": "",
                "theater_experiance": "",
                "group_to_theater_experiance": False,
                "sort_by": "showtime",
            }

            signature = generate_signature(body, secret_key, timestamp)

            headers = {
                "Content-Type": "application/json",
                "lang-id": "1",
                "Signature": signature,
                "Timestamp": str(timestamp),
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " "AppleWebKit/537.36"
                ),
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()

                json_response = response.json()
                data = json_response.get("data", {})
                movies = data.get("movies", [])

                if not movies:
                    continue

                for movie in movies:
                    title = movie.get("movie_name")
                    if not title:
                        continue

                    show_times = movie.get("show_times", [])
                    for show_time in show_times:
                        time_slot = show_time.get("show_time_slots")
                        session_date = show_time.get("session_start_date")

                        if not time_slot or not session_date:
                            continue

                        # Parse the time slot (format: "4:20PM", "10:00PM", etc.)
                        try:
                            showtime_dt = datetime.strptime(
                                f"{session_date} {time_slot}", "%Y-%m-%d %I:%M%p"
                            )
                        except ValueError:
                            try:
                                showtime_dt = datetime.strptime(
                                    f"{session_date} {time_slot}", "%Y-%m-%d %I:%M %p"
                                )
                            except ValueError:
                                continue

                        time_text = showtime_dt.strftime("%H:%M")

                        key = (title, showtime_dt)
                        if key not in seen:
                            seen.add(key)
                            showtimes.append(
                                Showtime(
                                    cinema=self.cinema_name,
                                    location=self.location,
                                    title=title,
                                    time=time_text,
                                    date=showtime_dt,
                                )
                            )

        return showtimes


# Concrete providers for each FilmHouse location


class FilmHouseLandmarkProvider(FilmHouseProvider):
    """Provider for FilmHouse Cinemas Landmark."""

    cinema_name = "FilmHouse Cinemas"
    location = "Landmark, Lagos"
    cinema_location_id = "5"


class FilmHouseLekkiIMAXProvider(FilmHouseProvider):
    """Provider for FilmHouse Cinemas Lekki IMAX."""

    cinema_name = "FilmHouse Cinemas"
    location = "Lekki IMAX"
    cinema_location_id = "6"


class FilmHouseOniruProvider(FilmHouseProvider):
    """Provider for FilmHouse Cinemas Oniru."""

    cinema_name = "FilmHouse Cinemas"
    location = "Oniru"
    cinema_location_id = "10"


class FilmHousePalmsLekkiProvider(FilmHouseProvider):
    """Provider for FilmHouse Cinemas Palms Lekki."""

    cinema_name = "FilmHouse Cinemas"
    location = "Palms Lekki"
    cinema_location_id = "11"


class FilmHouseSurulereProvider(FilmHouseProvider):
    """Provider for FilmHouse Cinemas Surulere."""

    cinema_name = "FilmHouse Cinemas"
    location = "Surulere"
    cinema_location_id = "7"


class FilmHouseCircleMallProvider(FilmHouseProvider):
    """Provider for FilmHouse Cinemas Circle Mall."""

    cinema_name = "FilmHouse Cinemas"
    location = "Circle Mall"
    cinema_location_id = "8"


class FilmHouseIkotaProvider(FilmHouseProvider):
    """Provider for FilmHouse Cinemas Ikota."""

    cinema_name = "FilmHouse Cinemas"
    location = "Ikota"
    cinema_location_id = "9"
