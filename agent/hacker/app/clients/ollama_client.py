from langchain_ollama import ChatOllama
from app.config import config


def get_ollama_client(model: str | None = None, **kwargs) -> ChatOllama:
    """
    Factory function to create an Ollama client.

    Args:
        model: Model name to use. Defaults to config.OLLAMA_PLANNER_MODEL.
        **kwargs: Additional arguments passed to ChatOllama.

    Returns:
        Configured ChatOllama instance.
    """
    return ChatOllama(
        base_url=config.OLLAMA_BASE_URL,
        model=model or config.OLLAMA_PLANNER_MODEL,
        **kwargs
    )


def get_planner_client() -> ChatOllama:
    """Get Ollama client configured for the Planner agent."""
    return get_ollama_client(model=config.OLLAMA_PLANNER_MODEL)


def get_compiler_client() -> ChatOllama:
    """Get Ollama client configured for the Compiler agent."""
    return get_ollama_client(model=config.OLLAMA_COMPILER_MODEL)
