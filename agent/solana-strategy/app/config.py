"""Solana Strategy agent configuration."""

import os


class StrategyConfig:
    PORT = int(os.getenv("PORT", "8902"))

    # Where the trader service lives (Node + SAK).
    TRADER_BASE_URL = os.getenv("TRADER_BASE_URL", "http://localhost:8901")

    # Public price source for OHLCV (used by indicator tools). Birdeye is
    # the typical hackathon choice; the strategy degrades gracefully if missing.
    BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
    BIRDEYE_BASE_URL = os.getenv("BIRDEYE_BASE_URL", "https://public-api.birdeye.so")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    OPENAI_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    AGENT_ID = os.getenv("AGENT_ID", "solana-strategy")


config = StrategyConfig()
