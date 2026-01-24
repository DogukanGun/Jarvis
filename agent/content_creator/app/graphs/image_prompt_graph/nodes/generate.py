"""
Generate Node.

Generates an image from a text prompt.
"""
import logging
import tempfile
import os
from typing import Dict, Any, Literal

from app.schemas.messages import RenderRequest
from app.config import config
from app.graphs.image_prompt_graph.state import ImagePromptGraphState

logger = logging.getLogger(__name__)


def generate_node(state: ImagePromptGraphState) -> Dict[str, Any]:
    """
    Generate an image from the text prompt.

    Args:
        state: Current graph state with request

    Returns:
        State update with generation result
    """
    job_id = state.get("job_id", "unknown")
    request_dict = state.get("request", {})

    logger.info(f"Generating image for job {job_id}...")

    try:
        # Parse request
        request = RenderRequest(**request_dict)

        # Get generation parameters
        prompt = request.prompt
        width = request.output.width
        height = request.output.height
        guidance_scale = request.meta.guidance_scale or config.DEFAULT_GUIDANCE_SCALE
        num_steps = request.meta.num_inference_steps or config.DEFAULT_NUM_INFERENCE_STEPS
        seed = request.meta.seed
        negative_prompt = request.meta.negative_prompt

        # Get model
        from app.clients.model_client import get_image_model, get_best_device
        pipeline = get_image_model()

        # Set up generator for reproducibility
        import torch
        device = get_best_device()
        generator = None
        if seed is not None:
            # MPS doesn't support generator directly, use CPU generator
            gen_device = "cpu" if device == "mps" else device
            generator = torch.Generator(device=gen_device)
            generator.manual_seed(seed)
            logger.info(f"Using seed {seed} for job {job_id}")

        # Generate image
        logger.info(
            f"Generating {width}x{height} image with {num_steps} steps, "
            f"guidance_scale={guidance_scale} for job {job_id}"
        )

        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            num_inference_steps=num_steps,
            generator=generator,
        )

        # Get the generated image
        image = result.images[0]

        # Save to temporary file
        output_format = request.output.format.value
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"{job_id}.{output_format}")

        image.save(output_path)
        logger.info(f"Saved generated image to {output_path}")

        # Get actual seed used (if not specified, random one was used)
        actual_seed = seed if seed is not None else "random"

        return {
            "generation_success": True,
            "output_path": output_path,
            "generation_error": None,
            "generation_metadata": {
                "seed": actual_seed,
                "width": width,
                "height": height,
                "guidance_scale": guidance_scale,
                "num_inference_steps": num_steps,
            },
        }

    except Exception as e:
        logger.error(f"Generation failed for job {job_id}: {e}")
        return {
            "generation_success": False,
            "output_path": None,
            "generation_error": str(e),
            "error": f"Generation failed: {str(e)}",
        }


def generation_router(state: ImagePromptGraphState) -> Literal["upload", "error"]:
    """
    Conditional edge function to decide next node.

    Returns:
        "upload" if generation succeeded
        "error" if generation failed
    """
    if state.get("generation_success"):
        return "upload"
    return "error"
