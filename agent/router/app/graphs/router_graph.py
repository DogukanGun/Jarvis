"""
Router Graph Definition

LangGraph flow that orchestrates sub-agent communication:
  retrieve_memory -> classify_intent -> [tool invocation] -> generate_response -> write_memory -> END
"""

from langgraph.graph import StateGraph, END
import logging

from .state import RouterGraphState
from .nodes import (
    retrieve_memory,
    classify_intent,
    invoke_thinker,
    invoke_web_fetcher,
    invoke_swiss_knife,
    generate_response,
    write_memory,
)

logger = logging.getLogger(__name__)


def _intent_router(state: RouterGraphState) -> str:
    """Route to the appropriate tool node based on classified intent."""
    intent = state.get("intent", "chat")
    if intent == "research":
        return "research"
    elif intent == "web_fetch":
        return "web_fetch"
    elif intent == "security":
        return "security"
    elif intent == "visual":
        return "visual"
    else:
        return "chat"


def create_router_graph():
    """
    Create the router LangGraph.

    Flow:
    1. retrieve_memory - Get relevant conversation context
    2. classify_intent - LLM classifies intent + extracts tool args
    3. [conditional] - Route to tool node or straight to response
       - "chat" -> generate_response
       - "visual" -> generate_response (with image sent to GPT-4o vision)
       - "research" -> invoke_thinker -> generate_response
       - "web_fetch" -> invoke_web_fetcher -> generate_response
       - "security" -> invoke_swiss_knife -> generate_response
    4. generate_response - LLM generates final response with tool results
    5. write_memory - Persist exchange to memory
    6. END
    """
    graph = StateGraph(RouterGraphState)

    # Add nodes
    graph.add_node("retrieve_memory", retrieve_memory)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("invoke_thinker", invoke_thinker)
    graph.add_node("invoke_web_fetcher", invoke_web_fetcher)
    graph.add_node("invoke_swiss_knife", invoke_swiss_knife)
    graph.add_node("generate_response", generate_response)
    # write_memory is intentionally NOT in the graph — it is fired as a
    # background task in server.py after the WebSocket response is sent,
    # so it never blocks the client from receiving the answer.

    # Entry point
    graph.set_entry_point("retrieve_memory")

    # Memory -> Classify
    graph.add_edge("retrieve_memory", "classify_intent")

    # Classify -> conditional routing
    graph.add_conditional_edges(
        "classify_intent",
        _intent_router,
        {
            "chat": "generate_response",
            "visual": "generate_response",
            "research": "invoke_thinker",
            "web_fetch": "invoke_web_fetcher",
            "security": "invoke_swiss_knife",
        },
    )

    # Tool nodes -> generate_response
    graph.add_edge("invoke_thinker", "generate_response")
    graph.add_edge("invoke_web_fetcher", "generate_response")
    graph.add_edge("invoke_swiss_knife", "generate_response")

    # Response -> END (write_memory happens async in server.py)
    graph.add_edge("generate_response", END)

    return graph.compile()


# Default compiled graph
router_graph = create_router_graph()


def run_router(user_id: str, message: str, conversation_history: list = None) -> RouterGraphState:
    """
    Run the router graph end-to-end.

    Args:
        user_id: User identifier
        message: User message
        conversation_history: Optional prior messages

    Returns:
        Final state with response
    """
    initial_state: RouterGraphState = {
        "user_id": user_id,
        "message": message,
        "conversation_history": conversation_history or [],
        "tools_used": [],
        "tool_results": {},
    }

    try:
        result = router_graph.invoke(initial_state)
        logger.info(f"Router completed: intent={result.get('intent')}, tools={result.get('tools_used')}")
        # write_memory is not in the graph; call it here for the HTTP endpoint
        write_memory(result)
        return result
    except Exception as e:
        logger.error(f"Router graph error: {e}")
        initial_state["response"] = f"I encountered an error processing your request: {e}"
        initial_state["error"] = str(e)
        return initial_state
