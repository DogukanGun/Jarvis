"""
Configuration for Jarvis memory system
"""

import os
from pathlib import Path


class Config:
    """Configuration settings"""

    # =========================================================================
    # Mem0 settings (local server - no API key required)
    # =========================================================================
    MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")  # Optional for local setup
    MEM0_BASE_URL = os.getenv("MEM0_BASE_URL", "http://localhost:8080")

    # =========================================================================
    # LLM settings
    # =========================================================================
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # ollama, openai, mock
    LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # =========================================================================
    # Episode Storage (SQLite)
    # =========================================================================
    SQLITE_DB_PATH = os.getenv(
        "SQLITE_DB_PATH",
        str(Path(__file__).parent.parent / "jarvis_episodes.db")
    )

    # =========================================================================
    # Embedding settings
    # =========================================================================
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))

    # =========================================================================
    # Episode retrieval settings
    # =========================================================================
    EPISODE_RETRIEVE_LIMIT = int(os.getenv("EPISODE_RETRIEVE_LIMIT", "5"))
    EPISODE_MIN_IMPORTANCE = float(os.getenv("EPISODE_MIN_IMPORTANCE", "0.3"))

    # =========================================================================
    # Context composition settings
    # =========================================================================
    MAX_EPISODES_IN_CONTEXT = int(os.getenv("MAX_EPISODES_IN_CONTEXT", "5"))
    MAX_MEM0_ITEMS_IN_CONTEXT = int(os.getenv("MAX_MEM0_ITEMS_IN_CONTEXT", "10"))

    # =========================================================================
    # Memory write settings
    # =========================================================================
    ENABLE_MEMORY_WRITE = os.getenv("ENABLE_MEMORY_WRITE", "true").lower() == "true"

    # =========================================================================
    # Promotion settings (episode -> mem0)
    # =========================================================================
    PROMOTION_THRESHOLD_COUNT = int(os.getenv("PROMOTION_THRESHOLD_COUNT", "3"))
    PROMOTION_MIN_CONFIDENCE = float(os.getenv("PROMOTION_MIN_CONFIDENCE", "0.7"))
    PROMOTION_LOOKBACK_DAYS = int(os.getenv("PROMOTION_LOOKBACK_DAYS", "30"))

    # =========================================================================
    # Kafka settings
    # =========================================================================
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "jarvis-memory")
    KAFKA_APPROVAL_TIMEOUT_SECONDS = int(os.getenv("KAFKA_APPROVAL_TIMEOUT_SECONDS", "300"))

    # Kafka topics
    KAFKA_TOPIC_APPROVAL_REQUEST = os.getenv(
        "KAFKA_TOPIC_APPROVAL_REQUEST",
        "memory.approval.request"
    )
    KAFKA_TOPIC_APPROVAL_RESPONSE = os.getenv(
        "KAFKA_TOPIC_APPROVAL_RESPONSE",
        "memory.approval.response"
    )

    # =========================================================================
    # Reflection graph settings (periodic pattern extraction)
    # =========================================================================
    REFLECTION_SCHEDULE_HOURS = int(os.getenv("REFLECTION_SCHEDULE_HOURS", "6"))
    REFLECTION_LOOKBACK_DAYS = int(os.getenv("REFLECTION_LOOKBACK_DAYS", "7"))
    REFLECTION_MIN_PATTERN_COUNT = int(os.getenv("REFLECTION_MIN_PATTERN_COUNT", "2"))

    # =========================================================================
    # Background worker settings
    # =========================================================================
    MEMORY_WORKER_THREADS = int(os.getenv("MEMORY_WORKER_THREADS", "2"))


# Global config instance
config = Config()
