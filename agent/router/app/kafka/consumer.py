"""Kafka consumer for the Router agent.

Subscribes to the group events topic and forwards relevant agent lifecycle
events to all connected WebSocket clients via the ``broadcast_callback``.

This consumer is read-only — it never publishes back to Kafka.  It runs in
a daemon background thread so it does not block FastAPI's async event loop.
The broadcast callback is called via ``asyncio.run_coroutine_threadsafe`` so
the coroutine is safely scheduled on the main event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Callable, Coroutine, Dict, Optional

from app.config import config

logger = logging.getLogger(__name__)

# Event types from sub-agents that are interesting enough to push to the UI
_FORWARDED_EVENT_TYPES = {
    "task.started",
    "task.completed",
    "task.failed",
    "result.security_scan",
}


class RouterKafkaConsumer:
    """Read-only Kafka consumer that forwards agent events to WS clients.

    Args:
        broadcast_callback: An async callable ``(event: dict) -> None`` that
            sends the event to all connected WebSocket clients.  The main
            event loop is captured at construction time and used with
            ``asyncio.run_coroutine_threadsafe``.
        loop: The asyncio event loop to schedule broadcast coroutines on.
            Pass the loop captured in the FastAPI lifespan handler.
    """

    def __init__(
        self,
        broadcast_callback: Callable[[Dict[str, Any]], Coroutine],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._broadcast_callback = broadcast_callback
        self._loop = loop
        self._running = False
        self._consumer: Optional[Any] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Blocking loop — call this in a daemon thread."""
        from kafka import KafkaConsumer
        from kafka.errors import KafkaError

        topic = f"group.{config.GROUP_ID}.events"

        logger.info(
            "RouterKafkaConsumer: connecting to %s, topic=%s",
            config.KAFKA_BROKERS,
            topic,
        )

        try:
            self._consumer = KafkaConsumer(
                topic,
                bootstrap_servers=[config.KAFKA_BROKERS],
                group_id=f"{config.AGENT_ID}-consumer-group",
                auto_offset_reset="latest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                consumer_timeout_ms=1000,  # allows checking self._running
            )
        except KafkaError as exc:
            logger.error("RouterKafkaConsumer: failed to connect: %s", exc)
            return

        self._running = True
        logger.info("RouterKafkaConsumer: started, listening on %s", topic)

        try:
            while self._running:
                try:
                    for msg in self._consumer:
                        if not self._running:
                            break
                        self._handle_message(msg.value)
                except StopIteration:
                    # consumer_timeout_ms hit — loop to check self._running
                    pass
                except Exception as exc:
                    logger.error("RouterKafkaConsumer: error processing message: %s", exc)
        finally:
            self._consumer.close()
            logger.info("RouterKafkaConsumer: stopped")

    def close(self) -> None:
        """Signal the consumer loop to stop."""
        self._running = False

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    def _handle_message(self, envelope: Dict[str, Any]) -> None:
        if not isinstance(envelope, dict):
            return

        event_type: str = envelope.get("type", "")
        if event_type not in _FORWARDED_EVENT_TYPES:
            return

        sender_id = envelope.get("sender", {}).get("id", "unknown")
        payload = envelope.get("payload", {})

        ws_event: Dict[str, Any] = {
            "type": "agent_event",
            "event_type": event_type,
            "sender": sender_id,
            "thread_id": envelope.get("thread_id"),
            "timestamp": envelope.get("timestamp"),
        }

        if event_type == "task.completed":
            result_data = payload.get("result", {})
            ws_event["task_id"] = payload.get("task_id")
            # result_data is the full run_tool_graph dict: response, findings, tools_used, report
            if isinstance(result_data, dict):
                ws_event["response"] = result_data.get("response", "")
                ws_event["tools_used"] = result_data.get("tools_used", [])
                ws_event["findings"] = result_data.get("findings", [])
                ws_event["report"] = result_data.get("report", {})
            else:
                ws_event["response"] = str(result_data)
                ws_event["tools_used"] = []
                ws_event["findings"] = []
                ws_event["report"] = {}

        elif event_type == "result.security_scan":
            ws_event["task_id"] = payload.get("task_id")
            ws_event["data"] = payload.get("data", {})
            ws_event["success"] = payload.get("success", False)

        elif event_type == "task.failed":
            ws_event["task_id"] = payload.get("task_id")
            ws_event["error"] = payload.get("error", "")

        elif event_type == "task.started":
            ws_event["task_id"] = payload.get("task_id")
            ws_event["target_agent"] = payload.get("target_agent", "")

        logger.info(
            "RouterKafkaConsumer: forwarding %s from %s to WS clients",
            event_type,
            sender_id,
        )
        self._schedule_broadcast(ws_event)

    def _schedule_broadcast(self, event: Dict[str, Any]) -> None:
        """Thread-safely schedule the async broadcast on the main event loop."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast_callback(event),
                self._loop,
            )
        else:
            logger.warning(
                "RouterKafkaConsumer: main event loop not available, dropping event %s",
                event.get("event_type"),
            )
