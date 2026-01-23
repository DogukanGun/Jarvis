"""
Upload Result Node.

Uploads the encoded video to MinIO storage.
"""
import logging
import os
from typing import Dict, Any

from app.clients.storage_client import get_storage_client
from app.graphs.video_graph.state import VideoGraphState

logger = logging.getLogger(__name__)


def upload_result_node(state: VideoGraphState) -> Dict[str, Any]:
    """
    Upload the encoded video to storage.

    Args:
        state: Current graph state with output_path

    Returns:
        State update with upload result
    """
    job_id = state.get("job_id", "unknown")
    output_path = state.get("output_path")

    if not output_path:
        logger.error(f"No output path for job {job_id}")
        return {
            "upload_success": False,
            "upload_error": "No output path",
            "error": "No output path for upload",
        }

    logger.info(f"Uploading video result for job {job_id}...")

    try:
        storage = get_storage_client()
        result = storage.upload_file(
            file_path=output_path,
            job_id=job_id,
        )

        if result["success"]:
            logger.info(f"Uploaded video to {result['url']} for job {job_id}")

            # Clean up temp file and directory
            try:
                os.remove(output_path)
                # Also remove the temp directory if empty
                temp_dir = os.path.dirname(output_path)
                if temp_dir and os.path.isdir(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                logger.debug(f"Cleaned up temp file and directory for {output_path}")
            except Exception:
                pass

            return {
                "upload_success": True,
                "response_url": result["url"],
                "upload_error": None,
            }
        else:
            logger.error(f"Upload failed for job {job_id}: {result['error']}")
            return {
                "upload_success": False,
                "upload_error": result["error"],
                "error": f"Upload failed: {result['error']}",
            }

    except Exception as e:
        logger.error(f"Upload error for job {job_id}: {e}")
        return {
            "upload_success": False,
            "upload_error": str(e),
            "error": f"Upload failed: {str(e)}",
        }
