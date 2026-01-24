from datetime import datetime

from logging_config import get_logger
from models import Showtime
from providers.utils import LAGOS_TZ

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

    now = datetime.now(LAGOS_TZ)
    if showtime.date.date() < now.date():
        logger.debug(
            f"Showtime date is in the past: {showtime.date.date()} "
            f"for {showtime.title} at {showtime.cinema}"
        )
        return False

    return True


def validate_showtimes(showtimes: list[Showtime]) -> list[Showtime]:
    """
    Filter and validate a list of showtimes, normalizing all datetimes to (UTC+1).

    Args:
        showtimes: List of Showtime objects

    Returns:
        List of valid Showtime objects with timezone-normalized dates
    """
    valid_showtimes = []
    invalid_count = 0

    for showtime in showtimes:
        # Normalize timezone: convert naive datetimes to Lagos timezone
        # or convert timezone-aware datetimes from other zones to Lagos timezone
        if isinstance(showtime.date, datetime):
            if showtime.date.tzinfo is None:
                # Naive datetime - assume it's in Lagos timezone
                showtime.date = showtime.date.replace(tzinfo=LAGOS_TZ)
            else:
                # Timezone-aware datetime - convert to Lagos timezone
                showtime.date = showtime.date.astimezone(LAGOS_TZ)

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
