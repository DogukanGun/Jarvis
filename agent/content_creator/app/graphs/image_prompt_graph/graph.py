"""
Image Prompt Graph.

Generates images from text prompts using Qwen-Image-2512.

Flow:
    START -> load_model -> generate --(success)--> upload_result -> publish_result -> END
                              |
                           (error)
                              v
                         handle_error -> END
"""
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from app.graphs.image_prompt_graph.state import ImagePromptGraphState
from app.graphs.image_prompt_graph.nodes import (
    load_model_node,
    generate_node,
    generation_router,
    upload_result_node,
    publish_result_node,
    handle_error_node,
)

logger = logging.getLogger(__name__)


def create_image_prompt_graph() -> StateGraph:
    """
    Create and compile the Image Prompt Graph.

    Returns:
        Compiled LangGraph ready for execution.
    """
    logger.info("Creating Image Prompt graph...")

    # Create graph with state schema
    graph = StateGraph(ImagePromptGraphState)

    # Add nodes
    graph.add_node("load_model", load_model_node)
    graph.add_node("generate", generate_node)
    graph.add_node("upload_result", upload_result_node)
    graph.add_node("publish_result", publish_result_node)
    graph.add_node("handle_error", handle_error_node)

    # Set entry point
    graph.set_entry_point("load_model")

    # Add edges
    graph.add_edge("load_model", "generate")

    # Conditional routing based on generation result
    graph.add_conditional_edges(
        "generate",
        generation_router,
        {
            "upload": "upload_result",
            "error": "handle_error",
        }
    )

    graph.add_edge("upload_result", "publish_result")
    graph.add_edge("publish_result", END)
    graph.add_edge("handle_error", END)

    # Compile and return
    compiled = graph.compile()
    logger.info("Image Prompt graph compiled successfully")

    return compiled


def run_image_prompt_graph(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Image Prompt Graph with the given request.

    Args:
        request: Parsed RenderRequest dict

    Returns:
        Final graph state
    """
    job_id = request.get("job_id", "unknown")
    logger.info(f"Processing image prompt request: {job_id}")

    # Create graph
    graph = create_image_prompt_graph()

    # Build initial state
    initial_state: ImagePromptGraphState = {
        "request": request,
        "job_id": job_id,
    }

    # Run graph
    try:
        result = graph.invoke(initial_state)
        logger.info(f"Image Prompt graph completed for job {job_id}")
        return result
    except Exception as e:
        logger.error(f"Image Prompt graph failed: {str(e)}")
        raise
