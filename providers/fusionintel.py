"""Base class for FusionIntel API-based cinema providers."""

import os
from abc import abstractmethod

from dotenv import load_dotenv

from models import Showtime
from providers.base import BaseProvider
from providers.utils import fetch_fusionintel_showtimes

load_dotenv()


class FusionIntelProvider(BaseProvider):
    """
    Base class for all FusionIntel API-based cinema providers.

    Subclasses must define:
    - cinema_name: Name of the cinema
    - location: Location of the cinema
    - token_env_var: Environment variable name for the bearer token
    - base_movie_url: Base Movie URL

    Optionally override:
    - cinema_id: Cinema ID parameter (defaults to None)
    """

    @property
    @abstractmethod
    def cinema_name(self) -> str:
        """Name of the cinema (e.g., "EbonyLife Cinemas", "Viva Cinemas")."""
        pass

    @property
    @abstractmethod
    def location(self) -> str:
        """Location of the cinema (e.g., "Victoria Island, Lagos")."""
        pass

    @property
    @abstractmethod
    def token_env_var(self) -> str:
        """Environment variable name for the bearer token."""
        pass

    @property
    def cinema_id(self) -> str | None:
        """
        Cinema ID parameter for the FusionIntel API.

        Override this property if the cinema requires a cinema_id parameter.
        Defaults to None (no cinema_id needed).
        """
        return None

    @property
    @abstractmethod
    def base_movie_url(self) -> str:
        pass

    async def fetch(self) -> list[Showtime]:
        """
        Fetch showtimes from FusionIntel API.

        Returns:
            List of Showtime objects.

        Raises:
            ValueError: If the token environment variable is not set.
        """
        token = os.getenv(self.token_env_var)
        if not token:
            raise ValueError(f"{self.token_env_var} environment variable not set")

        return await fetch_fusionintel_showtimes(
            cinema_name=self.cinema_name,
            location_name=self.location,
            bearer_token=token,
            cinema_id=self.cinema_id,
            base_movie_url=self.base_movie_url,
            num_days=5,
        )
