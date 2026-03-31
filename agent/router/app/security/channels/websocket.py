"""WebSocket notification channel.

Broadcasts security events to all active WebSocket clients using the existing
_ws_clients registry from server.py. This reuses the same broadcast pattern
as the Kafka consumer — no new infrastructure needed.

Event → WS message mapping:
  intruder_detected → {type: "security_alert", message, image_b64, timestamp}
  alarm_triggered   → {type: "alarm"}
  guard_started     → {type: "status", content: "Guard mode activated"}
  guard_stopped     → {type: "status", content: "Guard mode deactivated"}
"""

import logging
from typing import Any, Set

from fastapi import WebSocket

from app.security.channels.base import SecurityChannel
from app.security.event_bus import SecurityEvent

logger = logging.getLogger(__name__)


class WebSocketChannel(SecurityChannel):
    name = "websocket"

    def __init__(self, ws_clients: Set[WebSocket]) -> None:
        # Holds a live reference to the set in server.py — always reflects current connections
        self._clients = ws_clients

    def is_open(self) -> bool:
        return True  # Always active; zero clients is fine (broadcast is a no-op)

    async def handle(self, event: SecurityEvent) -> None:
        payload = self._build_payload(event)
        if payload is None:
            return

        dead = set()
        for ws in list(self._clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)

        if dead:
            self._clients.difference_update(dead)
            logger.debug("WebSocketChannel removed %d dead connection(s)", len(dead))

        logger.info(
            "WebSocket broadcast '%s' to %d client(s)",
            event.type,
            len(self._clients),
        )

    def _build_payload(self, event: SecurityEvent) -> dict[str, Any] | None:
        if event.type == "intruder_detected":
            return {
                "type": "security_alert",
                "message": event.message,
                "image_b64": event.image_b64,
                "timestamp": event.timestamp,
            }
        if event.type == "alarm_triggered":
            return {"type": "alarm"}
        if event.type == "guard_started":
            return {"type": "status", "content": "Guard mode activated"}
        if event.type == "guard_stopped":
            return {"type": "status", "content": "Guard mode deactivated"}
        return None
