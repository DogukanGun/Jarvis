"""Swiss Army Knife agent configuration."""

import os


class SwissKnifeConfig:
    # Server
    PORT = int(os.getenv("PORT", "8787"))

    # LLM — set LLM_PROVIDER to: ollama | openai | anthropic | claude-code
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    # Ollama (default)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Anthropic
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # Claude Code CLI (local)
    CLAUDE_CODE_PATH = os.getenv("CLAUDE_CODE_PATH", "claude")

    # Kafka
    KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9094")
    GROUP_ID = os.getenv("GROUP_ID", "jarvis-main")
    AGENT_ID = os.getenv("AGENT_ID", "swiss-army-knife")
    ENABLE_GROUP_LAYER = os.getenv("ENABLE_GROUP_LAYER", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # Confirmation
    CONFIRMATION_TIMEOUT = int(os.getenv("CONFIRMATION_TIMEOUT", "300"))


config = SwissKnifeConfig()
