"""
Image Reference Graph.

Generates images from prompts with reference images using Qwen-Image-Edit-2511.

Flow:
    START -> download_reference --(success)--> load_model -> generate --(success)--> upload_result -> publish_result -> END
                   |                                            |
                (error)                                      (error)
                   v                                            v
              handle_error <------------------------------------+
"""
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from app.graphs.image_reference_graph.state import ImageReferenceGraphState
from app.graphs.image_reference_graph.nodes import (
    download_reference_node,
    download_router,
    load_model_node,
    generate_node,
    generation_router,
    upload_result_node,
    publish_result_node,
    handle_error_node,
)

logger = logging.getLogger(__name__)


def create_image_reference_graph() -> StateGraph:
    """
    Create and compile the Image Reference Graph.

    Returns:
        Compiled LangGraph ready for execution.
    """
    logger.info("Creating Image Reference graph...")

    graph = StateGraph(ImageReferenceGraphState)

    # Add nodes
    graph.add_node("download_reference", download_reference_node)
    graph.add_node("load_model", load_model_node)
    graph.add_node("generate", generate_node)
    graph.add_node("upload_result", upload_result_node)
    graph.add_node("publish_result", publish_result_node)
    graph.add_node("handle_error", handle_error_node)

    # Set entry point
    graph.set_entry_point("download_reference")

    # Add edges
    graph.add_conditional_edges(
        "download_reference",
        download_router,
        {
            "load": "load_model",
            "error": "handle_error",
        }
    )

    graph.add_edge("load_model", "generate")

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

    compiled = graph.compile()
    logger.info("Image Reference graph compiled successfully")

    return compiled


def run_image_reference_graph(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Image Reference Graph with the given request.

    Args:
        request: Parsed RenderRequest dict

    Returns:
        Final graph state
    """
    job_id = request.get("job_id", "unknown")
    logger.info(f"Processing image reference request: {job_id}")

    graph = create_image_reference_graph()

    initial_state: ImageReferenceGraphState = {
        "request": request,
        "job_id": job_id,
    }

    try:
        result = graph.invoke(initial_state)
        logger.info(f"Image Reference graph completed for job {job_id}")
        return result
    except Exception as e:
        logger.error(f"Image Reference graph failed: {str(e)}")
        raise
