from datetime import datetime

from logging_config import get_logger
from models import Showtime

logger = get_logger(__name__)


def validate_showtime(showtime: Showtime) -> bool:
    if not showtime.cinema or not showtime.cinema.strip():
        logger.warning("Showtime missing cinema name")
        return False

    if not showtime.location or not showtime.location.strip():
        logger.warning("Showtime missing location")
        return False

    if not showtime.title or not showtime.title.strip():
        logger.warning("Showtime missing title")
        return False

    if not showtime.time or not showtime.time.strip():
        logger.warning("Showtime missing time")
        return False

    if not isinstance(showtime.date, datetime):
        logger.warning(f"Invalid date type: {type(showtime.date)}")
        return False

    now = datetime.now()
    if showtime.date.date() < now.date():
        logger.debug(
            f"Showtime date is in the past: {showtime.date.date()} "
            f"for {showtime.title} at {showtime.cinema}"
        )
        return False

    return True


def validate_showtimes(showtimes: list[Showtime]) -> list[Showtime]:
    """
    Filter and validate a list of showtimes.

    Args:
        showtimes: List of Showtime objects

    Returns:
        List of valid Showtime objects
    """
    valid_showtimes = []
    invalid_count = 0

    for showtime in showtimes:
        if validate_showtime(showtime):
            valid_showtimes.append(showtime)
        else:
            invalid_count += 1

    if invalid_count > 0:
        logger.info(
            f"Filtered out {invalid_count} invalid showtimes "
            f"({len(valid_showtimes)} valid)"
        )

    return valid_showtimes


def deduplicate_showtimes(showtimes: list[Showtime]) -> list[Showtime]:
    seen = set()
    unique_showtimes = []

    for showtime in showtimes:
        key = (showtime.cinema, showtime.title, showtime.date)

        if key not in seen:
            seen.add(key)
            unique_showtimes.append(showtime)

    duplicates = len(showtimes) - len(unique_showtimes)
    if duplicates > 0:
        logger.info(f"Removed {duplicates} duplicate showtimes")

    return unique_showtimes
