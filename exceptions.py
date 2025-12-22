class ProviderError(Exception):
    """Base exception for all provider errors."""

    def __init__(self, provider_name: str, message: str):
        self.provider_name = provider_name
        self.message = message
        super().__init__(f"{provider_name}: {message}")


class AuthenticationError(ProviderError):
    """Raised when authentication fails."""

    pass


class ParsingError(ProviderError):
    """Raised when HTML/JSON parsing fails."""

    pass


class NoShowtimesFoundError(ProviderError):
    """Raised when no showtimes are found (may be expected)."""

    pass
