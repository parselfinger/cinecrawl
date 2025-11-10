from dataclasses import dataclass
from datetime import datetime


@dataclass
class Showtime:
    cinema: str
    location: str
    title: str
    time: str
    date: datetime | None = None


@dataclass
class CinemaResult:
    """Result from scraping a cinema"""

    cinema: str
    success: bool
    showtimes: list[Showtime]
    error: str | None = None
