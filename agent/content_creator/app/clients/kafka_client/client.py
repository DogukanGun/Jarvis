"""
Kafka Client for Media Rendering Pipeline.

Handles Kafka producer/consumer for media render requests and results.
"""
import json
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConsumedMessage:
    """Represents a consumed Kafka message."""
    topic: str
    partition: int
    offset: int
    key: Optional[str]
    value: Dict[str, Any]


class KafkaMediaClient:
    """
    Kafka client for media rendering communication.

    Handles:
    - Publishing render requests to worker topics
    - Publishing render results
    - Consuming messages from worker topics
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "content-creator",
    ):
        """
        Initialize Kafka client.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            group_id: Consumer group ID
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self._producer = None
        self._consumer = None
        self._subscribed_topics: set = set()

    def _init_producer(self):
        """Initialize Kafka producer lazily."""
        if self._producer is None:
            try:
                from kafka import KafkaProducer
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    acks='all',
                    retries=3,
                )
                logger.info("Kafka producer initialized")
            except ImportError:
                logger.warning("kafka-python not installed, using mock producer")
                self._producer = MockProducer()
            except Exception as e:
                logger.warning(f"Kafka producer init failed: {e}, using mock")
                self._producer = MockProducer()

    def _init_consumer(self, topics: List[str]):
        """
        Initialize Kafka consumer with specified topics.

        Args:
            topics: List of topics to subscribe to
        """
        topics_set = set(topics)

        # Only reinitialize if topics changed
        if self._consumer is not None and self._subscribed_topics == topics_set:
            return

        # Close existing consumer if any
        if self._consumer is not None:
            try:
                self._consumer.close()
            except Exception:
                pass

        try:
            from kafka import KafkaConsumer
            self._consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                consumer_timeout_ms=1000,
            )
            self._subscribed_topics = topics_set
            logger.info(f"Kafka consumer initialized for topics: {topics}")
        except ImportError:
            logger.warning("kafka-python not installed, using mock consumer")
            self._consumer = MockConsumer()
            self._subscribed_topics = topics_set
        except Exception as e:
            logger.warning(f"Kafka consumer init failed: {e}, using mock")
            self._consumer = MockConsumer()
            self._subscribed_topics = topics_set

    def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None,
    ) -> bool:
        """
        Publish a message to a Kafka topic.

        Args:
            topic: Target topic
            message: Message dict to publish
            key: Optional partition key

        Returns:
            True if successful, False otherwise
        """
        self._init_producer()

        try:
            future = self._producer.send(topic, key=key, value=message)
            self._producer.flush()
            future.get(timeout=10)  # Wait for confirmation
            logger.debug(f"Published to {topic}: {message.get('job_id', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False

    def consume(
        self,
        topics: List[str],
        timeout_ms: int = 1000,
        max_records: int = 10,
    ) -> List[ConsumedMessage]:
        """
        Consume messages from Kafka topics.

        Args:
            topics: Topics to consume from
            timeout_ms: Poll timeout in milliseconds
            max_records: Maximum records to return

        Returns:
            List of consumed messages
        """
        self._init_consumer(topics)
        messages = []

        try:
            result = self._consumer.poll(timeout_ms=timeout_ms, max_records=max_records)

            if hasattr(result, 'items'):
                # Real Kafka consumer returns dict
                for topic_partition, records in result.items():
                    for record in records:
                        messages.append(ConsumedMessage(
                            topic=record.topic,
                            partition=record.partition,
                            offset=record.offset,
                            key=record.key,
                            value=record.value,
                        ))
            elif result:
                # Mock consumer might return list
                for msg in result:
                    if isinstance(msg, dict):
                        messages.append(ConsumedMessage(
                            topic=topics[0] if topics else "unknown",
                            partition=0,
                            offset=0,
                            key=None,
                            value=msg,
                        ))

        except Exception as e:
            logger.error(f"Consume error: {e}")

        return messages

    def consume_one(
        self,
        topics: List[str],
        timeout_ms: int = 5000,
    ) -> Optional[ConsumedMessage]:
        """
        Consume a single message from Kafka topics.

        Args:
            topics: Topics to consume from
            timeout_ms: Poll timeout in milliseconds

        Returns:
            Single consumed message or None
        """
        messages = self.consume(topics, timeout_ms=timeout_ms, max_records=1)
        return messages[0] if messages else None

    def run_consumer_loop(
        self,
        topics: List[str],
        handler: Callable[[ConsumedMessage], None],
        poll_timeout_ms: int = 1000,
    ):
        """
        Run a continuous consumer loop.

        Args:
            topics: Topics to consume from
            handler: Function to handle each message
            poll_timeout_ms: Poll timeout in milliseconds
        """
        logger.info(f"Starting consumer loop for topics: {topics}")
        self._init_consumer(topics)

        try:
            while True:
                messages = self.consume(topics, timeout_ms=poll_timeout_ms)
                for msg in messages:
                    try:
                        handler(msg)
                    except Exception as e:
                        logger.error(f"Handler error for {msg.value.get('job_id', 'unknown')}: {e}")
        except KeyboardInterrupt:
            logger.info("Consumer loop interrupted")
        finally:
            self.close()

    def close(self):
        """Close Kafka connections."""
        if self._producer:
            try:
                self._producer.close()
                logger.info("Kafka producer closed")
            except Exception:
                pass
        if self._consumer:
            try:
                self._consumer.close()
                logger.info("Kafka consumer closed")
            except Exception:
                pass


class MockProducer:
    """Mock Kafka producer for testing/fallback."""

    def send(self, topic: str, key: str = None, value: dict = None):
        logger.debug(f"[MOCK] Would send to {topic}: {value}")

        class FutureResult:
            def get(self, timeout=None):
                return None

        return FutureResult()

    def flush(self):
        pass

    def close(self):
        pass


class MockConsumer:
    """Mock Kafka consumer for testing/fallback."""

    def poll(self, timeout_ms: int = 1000, max_records: int = 10):
        return {}

    def close(self):
        pass


# Singleton instance
_client_instance: Optional[KafkaMediaClient] = None


def get_kafka_client() -> KafkaMediaClient:
    """
    Get singleton Kafka client instance.

    Returns:
        KafkaMediaClient instance
    """
    global _client_instance

    if _client_instance is None:
        from app.config import config
        _client_instance = KafkaMediaClient(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=config.KAFKA_GROUP_ID,
        )

    return _client_instance
