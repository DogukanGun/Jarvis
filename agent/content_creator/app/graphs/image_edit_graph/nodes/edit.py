"""
Edit Node.

Edits an image based on the prompt.
"""
import logging
import tempfile
import os
from typing import Dict, Any, Literal

from app.schemas.messages import RenderRequest
from app.config import config
from app.graphs.image_edit_graph.state import ImageEditGraphState

logger = logging.getLogger(__name__)


def edit_node(state: ImageEditGraphState) -> Dict[str, Any]:
    """
    Edit the source image based on prompt.

    Args:
        state: Current graph state with request and source_image

    Returns:
        State update with edit result
    """
    job_id = state.get("job_id", "unknown")
    request_dict = state.get("request", {})
    source_image = state.get("source_image")

    if source_image is None:
        return {
            "edit_success": False,
            "edit_error": "No source image",
            "error": "Source image not available",
        }

    logger.info(f"Editing image for job {job_id}...")

    try:
        # Parse request
        request = RenderRequest(**request_dict)

        # Get edit parameters
        prompt = request.prompt
        width = request.output.width
        height = request.output.height
        guidance_scale = request.meta.guidance_scale or config.DEFAULT_GUIDANCE_SCALE
        num_steps = request.meta.num_inference_steps or config.DEFAULT_NUM_INFERENCE_STEPS
        seed = request.meta.seed
        negative_prompt = request.meta.negative_prompt

        # Resize source image to target dimensions
        source_image = source_image.resize((width, height))

        # Get model
        from app.clients.model_client import get_image_edit_model, get_best_device
        pipeline = get_image_edit_model()

        # Set up generator for reproducibility
        import torch
        device = get_best_device()
        generator = None
        if seed is not None:
            gen_device = "cpu" if device == "mps" else device
            generator = torch.Generator(device=gen_device)
            generator.manual_seed(seed)
            logger.info(f"Using seed {seed} for job {job_id}")

        # Edit image
        # For editing, we typically use higher strength to apply more changes
        strength = 0.8  # How much to change the original image

        logger.info(
            f"Editing {width}x{height} image with {num_steps} steps, "
            f"strength={strength}, guidance_scale={guidance_scale} for job {job_id}"
        )

        result = pipeline(
            prompt=prompt,
            image=source_image,
            negative_prompt=negative_prompt,
            strength=strength,
            guidance_scale=guidance_scale,
            num_inference_steps=num_steps,
            generator=generator,
        )

        # Get the edited image
        image = result.images[0]

        # Save to temporary file
        output_format = request.output.format.value
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"{job_id}.{output_format}")

        image.save(output_path)
        logger.info(f"Saved edited image to {output_path}")

        return {
            "edit_success": True,
            "output_path": output_path,
            "edit_error": None,
            "edit_metadata": {
                "seed": seed if seed is not None else "random",
                "width": width,
                "height": height,
                "strength": strength,
                "guidance_scale": guidance_scale,
                "num_inference_steps": num_steps,
            },
        }

    except Exception as e:
        logger.error(f"Edit failed for job {job_id}: {e}")
        return {
            "edit_success": False,
            "output_path": None,
            "edit_error": str(e),
            "error": f"Edit failed: {str(e)}",
        }


def edit_router(state: ImageEditGraphState) -> Literal["upload", "error"]:
    """
    Conditional edge function to decide next node.
    """
    if state.get("edit_success"):
        return "upload"
    return "error"
