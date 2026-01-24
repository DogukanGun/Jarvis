"""Kafka client for media rendering pipeline."""
from app.clients.kafka_client.client import (
    KafkaMediaClient,
    ConsumedMessage,
    get_kafka_client,
)

__all__ = [
    "KafkaMediaClient",
    "ConsumedMessage",
    "get_kafka_client",
]
