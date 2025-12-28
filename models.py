from dataclasses import dataclass
from datetime import datetime


@dataclass
class Showtime:
    cinema: str
    location: str
    title: str
    time: str
    date: datetime
    screen_type: str = "2D"


@dataclass
class CinemaResult:
    cinema: str
    success: bool
    showtimes: list[Showtime]
    error: str | None = None
