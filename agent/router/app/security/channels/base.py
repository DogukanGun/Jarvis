"""Abstract base class for security notification channels."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.security.event_bus import SecurityEvent


class SecurityChannel(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique channel name for logging."""
        ...

    def is_open(self) -> bool:
        """Return True if this channel is configured and ready to handle events.

        Channels whose required config vars are missing return False and are
        silently skipped during broadcast — no errors, no noise.
        """
        return True

    @abstractmethod
    async def handle(self, event: "SecurityEvent") -> None:
        """Handle a security event.

        Called concurrently with all other open channels via asyncio.gather.
        Implementations should not raise — catch exceptions internally and log them.
        """
        ...
