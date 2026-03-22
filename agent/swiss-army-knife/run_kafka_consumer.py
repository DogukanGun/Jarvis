"""Entrypoint for the Swiss Army Knife Kafka consumer."""

import logging
from app.kafka.consumer import start_consumer

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    start_consumer()
