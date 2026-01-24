"""Tests for Kafka client."""
import pytest
from unittest.mock import patch, MagicMock

from app.clients.kafka_client.client import KafkaMediaClient, MockProducer, MockConsumer


class TestKafkaMediaClient:
    """Tests for KafkaMediaClient."""

    def test_init(self):
        """Test client initialization."""
        client = KafkaMediaClient(
            bootstrap_servers="localhost:9092",
            group_id="test-group",
        )

        assert client.bootstrap_servers == "localhost:9092"
        assert client.group_id == "test-group"
        assert client._producer is None
        assert client._consumer is None

    def test_publish_with_mock(self):
        """Test publishing with mock producer."""
        client = KafkaMediaClient()
        client._producer = MockProducer()

        success = client.publish(
            topic="test-topic",
            message={"key": "value"},
            key="test-key",
        )

        assert success is True

    def test_consume_empty(self):
        """Test consuming with no messages."""
        client = KafkaMediaClient()
        client._consumer = MockConsumer()
        client._subscribed_topics = {"test-topic"}

        messages = client.consume(
            topics=["test-topic"],
            timeout_ms=100,
        )

        assert messages == []


class TestMockProducer:
    """Tests for MockProducer."""

    def test_send(self):
        """Test mock producer send."""
        producer = MockProducer()
        future = producer.send("topic", key="key", value={"data": "value"})

        # Should return a future-like object
        assert future is not None
        assert future.get() is None

    def test_flush(self):
        """Test mock producer flush."""
        producer = MockProducer()
        producer.flush()  # Should not raise


class TestMockConsumer:
    """Tests for MockConsumer."""

    def test_poll(self):
        """Test mock consumer poll."""
        consumer = MockConsumer()
        result = consumer.poll(timeout_ms=100)

        assert result == {}

    def test_close(self):
        """Test mock consumer close."""
        consumer = MockConsumer()
        consumer.close()  # Should not raise
