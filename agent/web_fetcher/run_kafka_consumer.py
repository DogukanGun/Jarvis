#!/usr/bin/env python3
"""
Run script for the Web Fetcher Kafka consumer.
This starts the consumer which listens to group communication events.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from kafka_consumer import main

if __name__ == "__main__":
    main()
