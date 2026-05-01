"""Create the appropriate LangChain ChatModel from config."""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import config

logger = logging.getLogger(__name__)


def create_chat_model() -> BaseChatModel:
    provider = config.LLM_PROVIDER
    temperature = config.LLM_TEMPERATURE

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set.")
        return ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            temperature=temperature,
            timeout=60,
            max_retries=1,
        )

    if provider in ("anthropic", "claude-code"):
        from langchain_anthropic import ChatAnthropic

        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        return ChatAnthropic(
            api_key=config.ANTHROPIC_API_KEY,
            model_name=config.ANTHROPIC_MODEL,
            temperature=temperature,
            timeout=60,
            max_retries=1,
        )

    if provider != "ollama":
        logger.warning("Unknown LLM provider '%s'; falling back to Ollama.", provider)

    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=config.OLLAMA_BASE_URL,
        model=config.LLM_MODEL,
        temperature=temperature,
    )
