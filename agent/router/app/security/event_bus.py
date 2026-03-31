"""Security event bus — broadcasts events to all registered open channels concurrently.

Same pattern as broadcast_to_ws_clients: one call → every open channel gets the
event via asyncio.gather. One channel failing never blocks the others.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.security.channels.base import SecurityChannel

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    type: str  # "intruder_detected" | "alarm_triggered" | "guard_started" | "guard_stopped"
    message: str
    image_b64: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SecurityEventBus:
    def __init__(self) -> None:
        self._channels: list["SecurityChannel"] = []

    def register(self, channel: "SecurityChannel") -> None:
        self._channels.append(channel)
        logger.info("Security channel registered: %s", channel.name)

    async def broadcast(self, event: SecurityEvent) -> None:
        """Fire event to all open channels concurrently."""
        open_channels = [c for c in self._channels if c.is_open()]
        if not open_channels:
            logger.warning("Security event '%s' fired but no channels are open", event.type)
            return

        logger.info(
            "Broadcasting security event '%s' to %d channel(s): %s",
            event.type,
            len(open_channels),
            [c.name for c in open_channels],
        )

        results = await asyncio.gather(
            *(c.handle(event) for c in open_channels),
            return_exceptions=True,
        )

        for channel, result in zip(open_channels, results):
            if isinstance(result, Exception):
                logger.error("Channel '%s' failed to handle event: %s", channel.name, result)


# Module-level singleton imported by server.py
event_bus = SecurityEventBus()
