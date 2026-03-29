"""Create the appropriate LangChain ChatModel from config.

ClaudeCode (subprocess-based) is not supported here because it does not
implement the tool-calling interface required by AgentExecutor.  If
claude-code is configured we fall back to the Anthropic API client.
"""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import config

logger = logging.getLogger(__name__)


def create_chat_model() -> BaseChatModel:
    """Return a LangChain ChatModel based on the active LLM_PROVIDER config.

    Supported providers:
      - ``openai``      → ChatOpenAI (GPT-4o by default)
      - ``anthropic``   → ChatAnthropic (claude-3-5-sonnet by default)
      - ``claude-code`` → falls back to ChatAnthropic (ClaudeCode has no tool-calling API)
      - ``ollama``      → ChatOllama (any model served locally)
    """
    provider = config.LLM_PROVIDER
    temperature = config.LLM_TEMPERATURE

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not config.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Set it in your environment or switch LLM_PROVIDER to 'ollama'."
            )

        logger.info("Using OpenAI chat model: %s", config.OPENAI_MODEL)
        return ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            temperature=temperature,
            timeout=60,
            max_retries=1,
        )

    if provider in ("anthropic", "claude-code"):
        from langchain_anthropic import ChatAnthropic

        if provider == "claude-code":
            logger.warning(
                "claude-code provider does not support tool-calling; "
                "falling back to Anthropic API."
            )

        if not config.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Set it in your environment or switch LLM_PROVIDER to 'ollama'."
            )

        logger.info("Using Anthropic chat model: %s", config.ANTHROPIC_MODEL)
        return ChatAnthropic(
            api_key=config.ANTHROPIC_API_KEY,
            model_name=config.ANTHROPIC_MODEL,
            temperature=temperature,
            timeout=60,
            max_retries=1,
        )

    # Default: Ollama
    if provider != "ollama":
        logger.warning(
            "Unknown LLM provider '%s'; falling back to Ollama.", provider
        )

    from langchain_ollama import ChatOllama

    logger.info(
        "Using Ollama chat model: %s @ %s", config.LLM_MODEL, config.OLLAMA_BASE_URL
    )
    return ChatOllama(
        base_url=config.OLLAMA_BASE_URL,
        model=config.LLM_MODEL,
        temperature=temperature,
    )
