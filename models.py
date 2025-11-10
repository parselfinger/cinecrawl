from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Showtime:
    cinema: str
    location: str
    title: str
    time: str
    date: Optional[datetime] = None



@dataclass
class CinemaResult:
    """Result from scraping a cinema"""
    cinema: str
    success: bool
    showtimes: List[Showtime]
    error: Optional[str] = None