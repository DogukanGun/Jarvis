"""
LLM Step Node for MainGraph
Node 7: llm_step

Calls LLM with composed context and extracts response + memory intents.
"""

from typing import Dict, Any
from app.shared.types import MainGraphState
from app.clients.llm_client import get_llm_client


def llm_step(state: MainGraphState) -> Dict[str, Any]:
    """
    Call LLM with context and produce response + memory intents.

    Args:
        state: Current graph state (must contain llm_context)

    Returns:
        State updates with llm_output, memory_intents, llm_error
    """
    llm_context = state.get("llm_context")

    if not llm_context:
        return {
            "llm_output": "Error: No LLM context available",
            "memory_intents": _build_minimal_memory_intents(state),
            "llm_error": "llm_context is missing"
        }

    try:
        # Get LLM client (will use config or mock)
        client = get_llm_client()

        # Generate response
        response_text, memory_intents = client.generate(llm_context)

        # Ensure memory_intents always exists
        if memory_intents is None:
            memory_intents = _build_minimal_memory_intents(state)

        return {
            "llm_output": response_text,
            "memory_intents": memory_intents,
            "llm_error": None
        }

    except Exception as e:
        # Handle LLM errors gracefully
        error_message = f"LLM error: {str(e)}"

        return {
            "llm_output": "I apologize, but I encountered an error processing your request. Please try again.",
            "memory_intents": _build_minimal_memory_intents(state),
            "llm_error": error_message
        }


def _build_minimal_memory_intents(state: MainGraphState) -> Dict[str, Any]:
    """
    Build minimal memory intents from state.

    Args:
        state: Current state

    Returns:
        Minimal memory intents dict
    """
    return {
        "candidates": [],
        "signals": {
            "task_type": state.get("task_type"),
            "app": state.get("app"),
            "entities": state.get("entities", [])
        }
    }
