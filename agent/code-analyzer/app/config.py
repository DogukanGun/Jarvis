"""Code Analyzer agent configuration."""

import os


class CodeAnalyzerConfig:
    PORT = int(os.getenv("PORT", "8900"))
    INDEXER_PORT = int(os.getenv("INDEXER_PORT", "8901"))
    INDEXER_BASE_URL = os.getenv("INDEXER_BASE_URL", "http://localhost:8901")
    REPO_CACHE_DIR = os.getenv("REPO_CACHE_DIR", "/tmp/jarvis-repos")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    OPENAI_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9094")
    GROUP_ID = os.getenv("GROUP_ID", "jarvis-main")
    AGENT_ID = os.getenv("AGENT_ID", "code-analyzer")

    INDEXER_STARTUP_TIMEOUT = int(os.getenv("INDEXER_STARTUP_TIMEOUT", "30"))
    INDEX_POLL_INTERVAL = float(os.getenv("INDEX_POLL_INTERVAL", "2.0"))
    INDEX_TIMEOUT = int(os.getenv("INDEX_TIMEOUT", "300"))


config = CodeAnalyzerConfig()
