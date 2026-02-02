"""Configuration for the general agent."""

import os
from pydantic import BaseModel


class Config(BaseModel):
    """Agent configuration."""

    # LLM settings
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    # OpenAI settings (optional)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Tool server settings
    tool_server_url: str = os.getenv("TOOL_SERVER_URL", "http://localhost:3000")

    # Server settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))


def get_config() -> Config:
    """Get the configuration."""
    return Config()
