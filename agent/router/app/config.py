"""Router agent configuration."""

import os


class RouterConfig:
    ROUTER_PORT = int(os.getenv("ROUTER_PORT", "8888"))

    # LLM
    LLM_PROVIDER = os.getenv("ROUTER_LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("ROUTER_LLM_MODEL", "gpt-4o")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_TEMPERATURE = float(os.getenv("ROUTER_LLM_TEMPERATURE", "0.7"))

    # Kafka
    KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9094")
    GROUP_ID = os.getenv("GROUP_ID", "jarvis-main")
    AGENT_ID = os.getenv("AGENT_ID", "router")
    ENABLE_KAFKA_CONSUMER = os.getenv("ENABLE_KAFKA_CONSUMER", "true").lower() in ("true", "1", "yes")

    # Sub-agent URLs
    THINKER_BASE_URL = os.getenv("THINKER_BASE_URL", "http://localhost:8585")
    WEB_FETCHER_BASE_URL = os.getenv("WEB_FETCHER_BASE_URL", "http://localhost:8000")
    MEMORY_BASE_URL = os.getenv("MEMORY_BASE_URL", "http://localhost:8686")
    SWISS_KNIFE_BASE_URL = os.getenv("SWISS_KNIFE_BASE_URL", "http://localhost:8789")
    VISION_BASE_URL = os.getenv("VISION_BASE_URL", "http://localhost:8500")
    CODE_ANALYZER_BASE_URL = os.getenv("CODE_ANALYZER_BASE_URL", "http://localhost:8900")
    SOLANA_TRADER_BASE_URL = os.getenv("SOLANA_TRADER_BASE_URL", "http://localhost:8901")
    SOLANA_STRATEGY_BASE_URL = os.getenv("SOLANA_STRATEGY_BASE_URL", "http://localhost:8902")
    LEGAL_RAG_BASE_URL = os.getenv("LEGAL_RAG_BASE_URL", "http://localhost:8903")

    # Security notification channels
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")


config = RouterConfig()
