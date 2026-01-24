"""
Encode Video Node.

Encodes generated frames into a video file.
"""
import logging
import os
import shutil
from typing import Dict, Any, Literal

from app.schemas.messages import RenderRequest
from app.config import config
from app.graphs.video_graph.state import VideoGraphState

logger = logging.getLogger(__name__)


def encode_video_node(state: VideoGraphState) -> Dict[str, Any]:
    """
    Encode frames into a video file.

    Args:
        state: Current graph state with frames_path

    Returns:
        State update with encode result
    """
    job_id = state.get("job_id", "unknown")
    frames_path = state.get("frames_path")
    metadata = state.get("generation_metadata", {})
    request_dict = state.get("request", {})

    if not frames_path:
        logger.error(f"No frames path for job {job_id}")
        return {
            "encode_success": False,
            "encode_error": "No frames path",
            "error": "No frames to encode",
        }

    logger.info(f"Encoding video for job {job_id}...")

    try:
        # Get output format from request
        request = RenderRequest(**request_dict)
        output_format = request.output.format.value
        fps = metadata.get("fps", config.DEFAULT_VIDEO_FPS)

        # Output path
        output_path = os.path.join(
            os.path.dirname(frames_path),
            f"{job_id}.{output_format}"
        )

        # Get list of frame files
        frame_files = sorted([
            os.path.join(frames_path, f)
            for f in os.listdir(frames_path)
            if f.endswith(".png")
        ])

        if not frame_files:
            raise ValueError("No frame files found")

        logger.info(f"Encoding {len(frame_files)} frames at {fps} FPS to {output_path}")

        # Use imageio for video encoding
        try:
            import imageio
            writer = imageio.get_writer(
                output_path,
                fps=fps,
                codec='libx264',
                quality=8,
                pixelformat='yuv420p',
            )

            for frame_file in frame_files:
                frame = imageio.imread(frame_file)
                writer.append_data(frame)

            writer.close()

        except ImportError:
            # Fallback to opencv if imageio not available
            import cv2

            # Read first frame to get dimensions
            first_frame = cv2.imread(frame_files[0])
            height, width = first_frame.shape[:2]

            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            for frame_file in frame_files:
                frame = cv2.imread(frame_file)
                out.write(frame)

            out.release()

        logger.info(f"Video encoded to {output_path}")

        # Clean up frames directory
        try:
            shutil.rmtree(frames_path)
            logger.debug(f"Cleaned up frames directory {frames_path}")
        except Exception:
            pass

        return {
            "encode_success": True,
            "output_path": output_path,
            "encode_error": None,
        }

    except Exception as e:
        logger.error(f"Video encoding failed for job {job_id}: {e}")
        return {
            "encode_success": False,
            "output_path": None,
            "encode_error": str(e),
            "error": f"Video encoding failed: {str(e)}",
        }


def encode_router(state: VideoGraphState) -> Literal["upload", "error"]:
    """
    Conditional edge function to decide next node.
    """
    if state.get("encode_success"):
        return "upload"
    return "error"
