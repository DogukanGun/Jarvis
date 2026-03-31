"""Email notification channel.

Sends an email alert (with optional JPEG attachment) via SMTP.

Required env vars:
  SMTP_HOST        — e.g. smtp.gmail.com
  SMTP_PORT        — e.g. 587
  SMTP_USER        — sender address / login
  SMTP_PASS        — app password
  ALERT_EMAIL_TO   — recipient address
"""

import asyncio
import base64
import logging
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.security.channels.base import SecurityChannel
from app.security.event_bus import SecurityEvent

logger = logging.getLogger(__name__)

_SUBJECTS = {
    "intruder_detected": "Jarvis Security Alert: Intruder Detected",
    "alarm_triggered": "Jarvis Security Alert: Alarm Triggered",
    "guard_started": "Jarvis: Guard Mode Started",
    "guard_stopped": "Jarvis: Guard Mode Stopped",
}


class EmailChannel(SecurityChannel):
    name = "email"

    def __init__(self, config) -> None:
        self._host = config.SMTP_HOST
        self._port = config.SMTP_PORT
        self._user = config.SMTP_USER
        self._pass = config.SMTP_PASS
        self._to = config.ALERT_EMAIL_TO

    def is_open(self) -> bool:
        return all([self._host, self._user, self._pass, self._to])

    async def handle(self, event: SecurityEvent) -> None:
        await asyncio.to_thread(self._send_sync, event)

    def _send_sync(self, event: SecurityEvent) -> None:
        subject = _SUBJECTS.get(event.type, f"Jarvis Security: {event.type}")
        body = f"{event.message}\n\nTime: {event.timestamp}"

        msg = MIMEMultipart()
        msg["From"] = self._user
        msg["To"] = self._to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if event.image_b64 and event.type == "intruder_detected":
            image_bytes = base64.b64decode(event.image_b64)
            img = MIMEImage(image_bytes, name="intruder.jpg")
            img.add_header("Content-Disposition", "attachment", filename="intruder.jpg")
            msg.attach(img)

        try:
            with smtplib.SMTP(self._host, self._port) as smtp:
                smtp.starttls()
                smtp.login(self._user, self._pass)
                smtp.sendmail(self._user, self._to, msg.as_string())
            logger.info("Email notification sent for event '%s'", event.type)
        except Exception as e:
            logger.error("Email channel failed: %s", e)
