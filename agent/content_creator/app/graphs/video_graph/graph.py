"""
Video Graph.

Generates videos from text prompts using LTX-2 TI2VidTwoStagesPipeline.

Flow for LTX-2 (optimized - video encoded directly):
    START -> load_model -> generate_frames --(success+encoded)--> upload_result -> publish_result -> END
                               |
                            (error)
                               v
                          handle_error

Flow for legacy pipelines (frame-based):
    START -> load_model -> generate_frames --(success)--> encode_video --(success)--> upload_result -> publish_result -> END
                               |                              |
                            (error)                        (error)
                               v                              v
                          handle_error <----------------------+
"""
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from app.graphs.video_graph.state import VideoGraphState
from app.graphs.video_graph.nodes import (
    load_model_node,
    generate_frames_node,
    generation_router,
    encode_video_node,
    encode_router,
    upload_result_node,
    publish_result_node,
    handle_error_node,
)

logger = logging.getLogger(__name__)


def create_video_graph() -> StateGraph:
    """
    Create and compile the Video Graph.

    The graph supports both LTX-2 (direct video output) and legacy pipelines
    (frame-based output requiring encoding).

    Returns:
        Compiled LangGraph ready for execution.
    """
    logger.info("Creating Video graph...")

    graph = StateGraph(VideoGraphState)

    # Add nodes
    graph.add_node("load_model", load_model_node)
    graph.add_node("generate_frames", generate_frames_node)
    graph.add_node("encode_video", encode_video_node)
    graph.add_node("upload_result", upload_result_node)
    graph.add_node("publish_result", publish_result_node)
    graph.add_node("handle_error", handle_error_node)

    # Set entry point
    graph.set_entry_point("load_model")

    # Add edges
    graph.add_edge("load_model", "generate_frames")

    # Conditional routing after generation:
    # - "upload": LTX-2 path (video already encoded)
    # - "encode": Legacy path (need to encode frames)
    # - "error": Generation failed
    graph.add_conditional_edges(
        "generate_frames",
        generation_router,
        {
            "upload": "upload_result",
            "encode": "encode_video",
            "error": "handle_error",
        }
    )

    # Legacy encode path
    graph.add_conditional_edges(
        "encode_video",
        encode_router,
        {
            "upload": "upload_result",
            "error": "handle_error",
        }
    )

    graph.add_edge("upload_result", "publish_result")
    graph.add_edge("publish_result", END)
    graph.add_edge("handle_error", END)

    compiled = graph.compile()
    logger.info("Video graph compiled successfully")

    return compiled


def run_video_graph(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Video Graph with the given request.

    Args:
        request: Parsed RenderRequest dict

    Returns:
        Final graph state
    """
    job_id = request.get("job_id", "unknown")
    logger.info(f"Processing video request: {job_id}")

    graph = create_video_graph()

    initial_state: VideoGraphState = {
        "request": request,
        "job_id": job_id,
    }

    try:
        result = graph.invoke(initial_state)
        logger.info(f"Video graph completed for job {job_id}")
        return result
    except Exception as e:
        logger.error(f"Video graph failed: {str(e)}")
        raise
