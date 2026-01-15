"""
Kafka Client

Communication with main agent for memory approval flow.
"""

from .client import KafkaMemoryClient, get_kafka_client

__all__ = ["KafkaMemoryClient", "get_kafka_client"]
