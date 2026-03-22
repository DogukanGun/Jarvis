"""Router graph state definition."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class RouterGraphState(TypedDict, total=False):
    # Input
    user_id: str
    message: str
    conversation_history: List[Dict[str, Any]]

    # Classification
    intent: str  # "chat" | "research" | "web_fetch"
    tool_args: Dict[str, Any]

    # Memory
    memory_context: Dict[str, Any]
    memory_episodes: List[Dict[str, Any]]

    # Tool results
    tool_results: Dict[str, Any]
    tools_used: List[str]

    # Output
    response: str
    error: Optional[str]
