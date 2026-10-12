"""Atomic admission control for login attempts."""

from abc import ABC, abstractmethod


class ILoginRateLimiter(ABC):
    @abstractmethod
    def consume(self, *, client_ip: str, username: str) -> None:
        """Reserve one attempt for both keys or raise RateLimitExceeded."""
