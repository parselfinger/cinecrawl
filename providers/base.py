"""Base provider interface that all cinema providers must implement."""

from abc import ABC, abstractmethod

from models import Showtime


class BaseProvider(ABC):
    """
    Abstract base class for all cinema showtime providers.

    All providers must implement the fetch() method and provide
    cinema_name and location properties.
    """

    @abstractmethod
    async def fetch(self) -> list[Showtime]:
        """
        Fetch showtimes from the cinema data source.

        Returns:
            List of Showtime objects for this cinema.
        """
        pass

    @property
    @abstractmethod
    def cinema_name(self) -> str:
        """
        The name of the cinema (e.g., "FilmHouse Cinemas", "Viva Cinemas").

        Returns:
            Cinema name string.
        """
        pass

    @property
    @abstractmethod
    def location(self) -> str:
        """
        The location of the cinema (e.g., "Landmark, Lagos", "Ikeja, Lagos").

        Returns:
            Location string.
        """
        pass

    @property
    def display_name(self) -> str:
        """
        The full display name combining cinema and location.

        Returns:
            Full display name (e.g., "FilmHouse Cinemas, Landmark")
        """
        return f"{self.cinema_name}, {self.location}"
