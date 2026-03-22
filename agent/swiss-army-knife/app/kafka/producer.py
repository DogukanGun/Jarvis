"""
Kafka producer utility for the Swiss Army Knife agent.
Publishes events to the Jarvis group communication layer.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from kafka import KafkaProducer
from kafka.errors import KafkaError

from app.config import config

logger = logging.getLogger(__name__)


class SwissKnifeProducer:
    """Kafka producer for publishing security scan results."""

    def __init__(self, broker_url: str = None):
        self.broker_url = broker_url or config.KAFKA_BROKERS
        self.group_id = config.GROUP_ID
        self.agent_id = config.AGENT_ID
        self._producer = None

    @property
    def producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=[self.broker_url],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
            )
        return self._producer

    def _create_envelope(
        self,
        event_type: str,
        payload: Dict[str, Any],
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "message_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "thread_id": thread_id or str(uuid4()),
            "sender": {
                "id": self.agent_id,
                "role": "MEMBER",
                "agent": self.agent_id,
            },
            "type": event_type,
            "payload": payload,
            "version": "1.0",
        }

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        thread_id: Optional[str] = None,
    ) -> str:
        """Publish an event to the group events topic."""
        envelope = self._create_envelope(event_type, payload, thread_id)
        topic = f"group.{self.group_id}.events"

        try:
            future = self.producer.send(
                topic,
                value=envelope,
                key=envelope["thread_id"].encode("utf-8"),
            )
            future.get(timeout=10)
            logger.info(f"Published {event_type}: {envelope['message_id']}")
            return envelope["message_id"]
        except KafkaError as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    def publish_task_started(self, task_id: str, thread_id: str = None) -> str:
        return self.publish(
            "task.started",
            {"task_id": task_id, "agent": self.agent_id, "status": "started"},
            thread_id,
        )

    def publish_task_completed(
        self, task_id: str, result: Dict[str, Any], thread_id: str = None
    ) -> str:
        return self.publish(
            "task.completed",
            {"task_id": task_id, "agent": self.agent_id, "status": "completed", "result": result},
            thread_id,
        )

    def publish_task_failed(self, task_id: str, error: str, thread_id: str = None) -> str:
        return self.publish(
            "task.failed",
            {"task_id": task_id, "agent": self.agent_id, "status": "failed", "error": error},
            thread_id,
        )

    def publish_scan_result(
        self, task_id: str, findings: list, tools_used: list, thread_id: str = None
    ) -> str:
        return self.publish(
            "result.security_scan",
            {
                "task_id": task_id,
                "type": "security_scan",
                "data": {"findings": findings, "tools_used": tools_used},
                "success": True,
            },
            thread_id,
        )

    def close(self):
        if self._producer:
            self._producer.close()
            self._producer = None
