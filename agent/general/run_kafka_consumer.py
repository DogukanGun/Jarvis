#!/usr/bin/env python3
"""
Run script for the General Agent Kafka consumer.
This starts the consumer which listens to group communication events.
"""

import os
import sys

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from kafka_consumer import main

if __name__ == "__main__":
    main()
