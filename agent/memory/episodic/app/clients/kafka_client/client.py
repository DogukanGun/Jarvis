"""
Kafka Memory Client

Handles Kafka communication for memory approval workflow.
"""

import json
import uuid
import threading
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """Represents a pending approval request"""
    message_id: str
    proposal_id: str
    user_id: str
    expires_at: datetime
    response: Optional[Dict[str, Any]] = None


class KafkaMemoryClient:
    """
    Kafka client for memory approval communication.

    Handles:
    - Sending approval requests to main agent
    - Waiting for responses with timeout
    - Processing approval responses
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "jarvis-memory",
        request_topic: str = "memory.approval.request",
        response_topic: str = "memory.approval.response"
    ):
        """
        Initialize Kafka client.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            group_id: Consumer group ID
            request_topic: Topic for approval requests
            response_topic: Topic for approval responses
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.request_topic = request_topic
        self.response_topic = response_topic

        self._producer = None
        self._consumer = None
        self._pending: Dict[str, ApprovalRequest] = {}
        self._lock = threading.Lock()
        self._running = False
        self._consumer_thread: Optional[threading.Thread] = None

    def _init_producer(self):
        """Initialize Kafka producer lazily"""
        if self._producer is None:
            try:
                from kafka import KafkaProducer
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
                logger.info("Kafka producer initialized")
            except ImportError:
                logger.warning("kafka-python not installed, using mock producer")
                self._producer = MockProducer()
            except Exception as e:
                logger.warning(f"Kafka producer init failed: {e}, using mock")
                self._producer = MockProducer()

    def _init_consumer(self):
        """Initialize Kafka consumer lazily"""
        if self._consumer is None:
            try:
                from kafka import KafkaConsumer
                self._consumer = KafkaConsumer(
                    self.response_topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                    auto_offset_reset='latest',
                    consumer_timeout_ms=1000
                )
                logger.info("Kafka consumer initialized")
            except ImportError:
                logger.warning("kafka-python not installed, using mock consumer")
                self._consumer = MockConsumer()
            except Exception as e:
                logger.warning(f"Kafka consumer init failed: {e}, using mock")
                self._consumer = MockConsumer()

    def send_approval_request(
        self,
        proposal: Dict[str, Any],
        timeout_seconds: int = 300
    ) -> str:
        """
        Send approval request to main agent.

        Args:
            proposal: Promotion proposal dict
            timeout_seconds: Timeout before auto-reject

        Returns:
            Message ID for correlation
        """
        self._init_producer()

        message_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        # Build request message
        message = {
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "memory_promotion_request",
            "proposal": {
                "id": proposal.get("id"),
                "episode_id": proposal.get("episode_id"),
                "user_id": proposal.get("user_id"),
                "proposed_value": proposal.get("proposed_value"),
                "confidence": proposal.get("confidence"),
                "evidence": proposal.get("evidence", [])
            },
            "expires_at": expires_at.isoformat(),
            "display_message": self._build_display_message(proposal),
            "options": ["approve", "reject", "edit"]
        }

        # Track pending request
        with self._lock:
            self._pending[message_id] = ApprovalRequest(
                message_id=message_id,
                proposal_id=proposal.get("id"),
                user_id=proposal.get("user_id"),
                expires_at=expires_at
            )

        # Send to Kafka
        try:
            self._producer.send(
                self.request_topic,
                key=proposal.get("user_id"),
                value=message
            )
            self._producer.flush()
            logger.info(f"Sent approval request: {message_id}")
        except Exception as e:
            logger.error(f"Failed to send approval request: {e}")
            # Remove from pending on error
            with self._lock:
                self._pending.pop(message_id, None)
            raise

        return message_id

    def wait_for_response(
        self,
        message_id: str,
        timeout_seconds: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for approval response with timeout.

        Args:
            message_id: Message ID to wait for
            timeout_seconds: Max wait time

        Returns:
            Response dict or None if timeout
        """
        self._init_consumer()

        deadline = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        while datetime.utcnow() < deadline:
            # Check if we already have response
            with self._lock:
                pending = self._pending.get(message_id)
                if pending and pending.response:
                    return pending.response

            # Poll for messages
            try:
                messages = self._consumer.poll(timeout_ms=1000)

                if hasattr(messages, 'items'):
                    # Real Kafka consumer
                    for topic_partition, records in messages.items():
                        for record in records:
                            self._process_response(record.value)
                elif messages:
                    # Mock consumer returns list
                    for msg in messages:
                        self._process_response(msg)

            except Exception as e:
                logger.error(f"Error polling Kafka: {e}")

            # Check again after processing
            with self._lock:
                pending = self._pending.get(message_id)
                if pending and pending.response:
                    return pending.response

        # Timeout
        logger.warning(f"Timeout waiting for response: {message_id}")
        with self._lock:
            self._pending.pop(message_id, None)

        return None

    def _process_response(self, response: Dict[str, Any]):
        """Process an approval response message"""
        message_id = response.get("message_id")
        if not message_id:
            return

        with self._lock:
            if message_id in self._pending:
                self._pending[message_id].response = response
                logger.info(f"Received response for: {message_id}")

    def _build_display_message(self, proposal: Dict[str, Any]) -> str:
        """Build user-friendly display message"""
        value = proposal.get("proposed_value", "")
        confidence = proposal.get("confidence", 0)

        # Truncate if too long
        if len(value) > 150:
            value = value[:147] + "..."

        return (
            f"I've noticed a pattern in your behavior "
            f"(confidence: {confidence:.0%}):\n\n"
            f'"{value}"\n\n'
            f"Should I remember this?"
        )

    def get_pending_count(self) -> int:
        """Get count of pending requests"""
        with self._lock:
            return len(self._pending)

    def consume(
        self,
        topic: str,
        timeout_ms: int = 1000,
        max_records: int = 10
    ) -> list:
        """
        Consume messages from a Kafka topic.

        Args:
            topic: Topic to consume from
            timeout_ms: Poll timeout in milliseconds
            max_records: Max records to return

        Returns:
            List of message dicts
        """
        # Ensure we're subscribed to the right topic
        if self._consumer is None:
            self._init_consumer()

        # Handle topic switching if needed
        if hasattr(self._consumer, 'subscription'):
            current_topics = self._consumer.subscription()
            if topic not in current_topics:
                try:
                    self._consumer.subscribe([topic])
                except Exception:
                    pass

        messages = []
        try:
            result = self._consumer.poll(timeout_ms=timeout_ms)

            if hasattr(result, 'items'):
                # Real Kafka consumer returns dict
                for topic_partition, records in result.items():
                    for record in records[:max_records]:
                        messages.append(record.value)
                        if len(messages) >= max_records:
                            break
            elif result:
                # Mock consumer returns list
                messages = result[:max_records]

        except Exception as e:
            logger.error(f"Consume error: {e}")

        return messages

    def cleanup_expired(self) -> int:
        """Remove expired pending requests"""
        now = datetime.utcnow()
        expired = []

        with self._lock:
            for msg_id, request in self._pending.items():
                if request.expires_at < now:
                    expired.append(msg_id)

            for msg_id in expired:
                del self._pending[msg_id]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired requests")

        return len(expired)

    def close(self):
        """Close Kafka connections"""
        if self._producer:
            try:
                self._producer.close()
            except Exception:
                pass
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                pass


class MockProducer:
    """Mock Kafka producer for testing/fallback"""

    def send(self, topic: str, key: str = None, value: dict = None):
        logger.debug(f"[MOCK] Would send to {topic}: {value}")

    def flush(self):
        pass

    def close(self):
        pass


class MockConsumer:
    """Mock Kafka consumer for testing/fallback"""

    def poll(self, timeout_ms: int = 1000):
        return []

    def close(self):
        pass


# Factory function
_client_instance: Optional[KafkaMemoryClient] = None


def get_kafka_client() -> KafkaMemoryClient:
    """
    Get singleton Kafka client instance.

    Returns:
        KafkaMemoryClient instance
    """
    global _client_instance

    if _client_instance is None:
        from app.config import config
        _client_instance = KafkaMemoryClient(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=config.KAFKA_GROUP_ID,
            request_topic=config.KAFKA_TOPIC_APPROVAL_REQUEST,
            response_topic=config.KAFKA_TOPIC_APPROVAL_RESPONSE
        )

    return _client_instance
