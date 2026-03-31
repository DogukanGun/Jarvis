"""Telegram notification channel.

Sends a photo (for intruder_detected) or a text message (for other event types)
to the configured Telegram chat via the Bot API.

Required env vars:
  TELEGRAM_BOT_TOKEN — from @BotFather
  TELEGRAM_CHAT_ID   — your numeric chat ID (send /start to the bot, then
                       call getUpdates to find it)
"""

import base64
import logging

import httpx

from app.security.channels.base import SecurityChannel
from app.security.event_bus import SecurityEvent

logger = logging.getLogger(__name__)

_API = "https://api.telegram.org/bot{token}/{method}"

_EVENT_LABELS = {
    "intruder_detected": "Intruder detected on your laptop",
    "alarm_triggered": "Alarm triggered on your laptop",
    "guard_started": "Guard mode activated",
    "guard_stopped": "Guard mode deactivated",
}


class TelegramChannel(SecurityChannel):
    name = "telegram"

    def __init__(self, config) -> None:
        self._token = config.TELEGRAM_BOT_TOKEN
        self._chat_id = config.TELEGRAM_CHAT_ID

    def is_open(self) -> bool:
        return bool(self._token and self._chat_id)

    async def handle(self, event: SecurityEvent) -> None:
        label = _EVENT_LABELS.get(event.type, event.type)
        caption = f"{label}\n{event.message}\n{event.timestamp}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if event.image_b64 and event.type == "intruder_detected":
                    image_bytes = base64.b64decode(event.image_b64)
                    resp = await client.post(
                        _API.format(token=self._token, method="sendPhoto"),
                        data={"chat_id": self._chat_id, "caption": caption},
                        files={"photo": ("intruder.jpg", image_bytes, "image/jpeg")},
                    )
                else:
                    resp = await client.post(
                        _API.format(token=self._token, method="sendMessage"),
                        json={"chat_id": self._chat_id, "text": caption},
                    )
                resp.raise_for_status()
                logger.info("Telegram notification sent for event '%s'", event.type)
        except Exception as e:
            logger.error("Telegram channel failed: %s", e)
