"""Router agent configuration."""

import os


class RouterConfig:
    ROUTER_PORT = int(os.getenv("ROUTER_PORT", "8888"))

    # LLM
    LLM_PROVIDER = os.getenv("ROUTER_LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("ROUTER_LLM_MODEL", "llama3.1:8b")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_TEMPERATURE = float(os.getenv("ROUTER_LLM_TEMPERATURE", "0.7"))

    # Sub-agent URLs
    THINKER_BASE_URL = os.getenv("THINKER_BASE_URL", "http://localhost:8585")
    WEB_FETCHER_BASE_URL = os.getenv("WEB_FETCHER_BASE_URL", "http://localhost:8000")
    MEMORY_BASE_URL = os.getenv("MEMORY_BASE_URL", "http://localhost:8686")
    SWISS_KNIFE_BASE_URL = os.getenv("SWISS_KNIFE_BASE_URL", "http://localhost:8789")


config = RouterConfig()
