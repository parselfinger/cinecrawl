"""Retry logic for handling transient failures."""

import asyncio
import functools
from collections.abc import Callable
from typing import Any, TypeVar

import httpx

from logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def async_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.RemoteProtocolError,
        httpx.NetworkError,
    ),
):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"Failed after {max_attempts} attempts: {func.__name__}"
                        )
                        break

                    delay = backoff_factor**attempt
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: "
                        f"{type(e).__name__}. Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(
                        f"Error in {func.__name__}: " f"{type(e).__name__}: {str(e)}"
                    )
                    raise

            raise last_exception

        return wrapper

    return decorator
