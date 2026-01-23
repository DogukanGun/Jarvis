"""
Generate Video Node.

Generates video using the LTX-2 TI2VidTwoStagesPipeline.
The pipeline directly outputs encoded video with audio.
"""
import logging
import tempfile
import os
from typing import Dict, Any, Literal

from app.schemas.messages import RenderRequest
from app.config import config
from app.graphs.video_graph.state import VideoGraphState

logger = logging.getLogger(__name__)

# LTX-2 constants
AUDIO_SAMPLE_RATE = 24000
DEFAULT_NEGATIVE_PROMPT = (
    "blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, excessive noise, "
    "grainy texture, poor lighting, flickering, motion blur, distorted proportions, unnatural skin tones, "
    "deformed facial features, asymmetrical face, missing facial features, extra limbs, disfigured hands, "
    "wrong hand count, artifacts around text, inconsistent perspective, camera shake, incorrect depth of "
    "field, background too sharp, background clutter, distracting reflections, harsh shadows, inconsistent "
    "lighting direction, color banding, cartoonish rendering, 3D CGI look, unrealistic materials, uncanny "
    "valley effect, incorrect ethnicity, wrong gender, exaggerated expressions, wrong gaze direction, "
    "mismatched lip sync, silent or muted audio, distorted voice, robotic voice, echo, background noise, "
    "off-sync audio, incorrect dialogue, added dialogue, repetitive speech, jittery movement, awkward "
    "pauses, incorrect timing, unnatural transitions, inconsistent framing, tilted camera, flat lighting, "
    "inconsistent tone, cinematic oversaturation, stylized filters, or AI artifacts."
)


def generate_frames_node(state: VideoGraphState) -> Dict[str, Any]:
    """
    Generate video using LTX-2 TI2VidTwoStagesPipeline.

    This replaces the old frame-by-frame generation with direct video output.
    LTX-2 handles two-stage generation internally with upsampling.

    Args:
        state: Current graph state with request

    Returns:
        State update with generation result including output_path to video file
    """
    job_id = state.get("job_id", "unknown")
    request_dict = state.get("request", {})

    logger.info(f"Generating video with LTX-2 for job {job_id}...")

    try:
        # Parse request
        request = RenderRequest(**request_dict)

        # Get generation parameters with LTX-2 defaults
        prompt = request.prompt
        width = request.output.width or config.LTX_DEFAULT_WIDTH
        height = request.output.height or config.LTX_DEFAULT_HEIGHT
        fps = request.output.fps or config.LTX_DEFAULT_FRAME_RATE
        num_frames = request.meta.num_frames or config.LTX_DEFAULT_NUM_FRAMES
        cfg_guidance_scale = request.meta.guidance_scale or config.LTX_DEFAULT_CFG_GUIDANCE_SCALE
        num_steps = request.meta.num_inference_steps or config.LTX_DEFAULT_NUM_INFERENCE_STEPS
        seed = request.meta.seed if request.meta.seed is not None else 42
        negative_prompt = request.meta.negative_prompt or DEFAULT_NEGATIVE_PROMPT

        # Get model pipeline
        from app.clients.model_client import get_video_model

        pipeline = get_video_model()

        # Check if this is an LTX-2 pipeline
        pipeline_name = type(pipeline).__name__
        is_ltx2 = "TI2Vid" in pipeline_name or "LTX" in pipeline_name

        if is_ltx2:
            return _generate_with_ltx2(
                pipeline=pipeline,
                job_id=job_id,
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_frames=num_frames,
                fps=fps,
                cfg_guidance_scale=cfg_guidance_scale,
                num_steps=num_steps,
                seed=seed,
                output_format=request.output.format.value,
            )
        else:
            # Fallback to legacy frame-based generation
            return _generate_legacy(
                pipeline=pipeline,
                job_id=job_id,
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_frames=num_frames,
                fps=fps,
                guidance_scale=cfg_guidance_scale,
                num_steps=num_steps,
                seed=seed,
            )

    except Exception as e:
        logger.error(f"Video generation failed for job {job_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "generation_success": False,
            "output_path": None,
            "generation_error": str(e),
            "error": f"Video generation failed: {str(e)}",
        }


def _generate_with_ltx2(
    pipeline,
    job_id: str,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_frames: int,
    fps: float,
    cfg_guidance_scale: float,
    num_steps: int,
    seed: int,
    output_format: str,
) -> Dict[str, Any]:
    """
    Generate video using LTX-2 TI2VidTwoStagesPipeline.

    LTX-2 outputs video tensor and audio tensor directly, which we then encode.
    """
    from ltx_core.model.video_vae import TilingConfig, get_video_chunks_number
    from ltx_pipelines.utils.media_io import encode_video

    logger.info(
        f"LTX-2 generation: {width}x{height}, {num_frames} frames at {fps} FPS, "
        f"{num_steps} steps, cfg={cfg_guidance_scale}, seed={seed}"
    )

    # Use default tiling config for memory efficiency
    tiling_config = TilingConfig.default()
    video_chunks_number = get_video_chunks_number(num_frames, tiling_config)

    # Generate video with LTX-2 pipeline
    # images parameter is for optional image conditioning (empty list for text-only)
    video_output, audio_output = pipeline(
        prompt=prompt,
        negative_prompt=negative_prompt,
        seed=seed,
        height=height,
        width=width,
        num_frames=num_frames,
        frame_rate=fps,
        num_inference_steps=num_steps,
        cfg_guidance_scale=cfg_guidance_scale,
        images=[],  # No image conditioning for text-to-video
        tiling_config=tiling_config,
        enhance_prompt=False,  # Set to True to use Gemma for prompt enhancement
    )

    # Create output path
    temp_dir = tempfile.mkdtemp(prefix=f"video_{job_id}_")
    output_path = os.path.join(temp_dir, f"{job_id}.{output_format}")

    # Encode video with audio
    logger.info(f"Encoding video to {output_path}...")
    encode_video(
        video=video_output,
        fps=int(fps),
        audio=audio_output,
        audio_sample_rate=AUDIO_SAMPLE_RATE,
        output_path=output_path,
        video_chunks_number=video_chunks_number,
    )

    logger.info(f"Video generated successfully: {output_path}")

    return {
        "generation_success": True,
        "output_path": output_path,
        "encode_success": True,  # LTX-2 encodes directly, skip encode_video node
        "generation_error": None,
        "generation_metadata": {
            "seed": seed,
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "fps": fps,
            "cfg_guidance_scale": cfg_guidance_scale,
            "num_inference_steps": num_steps,
            "pipeline": "LTX-2 TI2VidTwoStagesPipeline",
        },
    }


def _generate_legacy(
    pipeline,
    job_id: str,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_frames: int,
    fps: float,
    guidance_scale: float,
    num_steps: int,
    seed: int,
) -> Dict[str, Any]:
    """
    Legacy frame-based video generation for non-LTX-2 pipelines.

    Returns frames for subsequent encoding by encode_video_node.
    """
    import torch
    from PIL import Image
    import numpy as np
    from app.clients.model_client import get_best_device

    # Cap frames for legacy models
    num_frames = min(num_frames, 24)

    # Set up generator for reproducibility
    device = get_best_device()
    generator = None
    if seed is not None:
        gen_device = "cpu" if device == "mps" else device
        generator = torch.Generator(device=gen_device)
        generator.manual_seed(seed)
        logger.info(f"Using seed {seed} for job {job_id}")

    logger.info(
        f"Legacy generation: {num_frames} frames at {width}x{height}, "
        f"{num_steps} steps, guidance_scale={guidance_scale}"
    )

    # Call pipeline
    result = pipeline(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        num_frames=num_frames,
        guidance_scale=guidance_scale,
        num_inference_steps=num_steps,
        generator=generator,
    )

    # Extract frames - handle different output formats
    frames = None
    if hasattr(result, 'frames'):
        frames = result.frames
        if isinstance(frames, list) and len(frames) > 0:
            if isinstance(frames[0], list):
                frames = frames[0]
    elif hasattr(result, 'images'):
        frames = result.images
    elif isinstance(result, tuple):
        frames = result[0]

    if frames is None:
        raise ValueError("Could not extract frames from model output")

    # Save frames to temporary directory
    temp_dir = tempfile.mkdtemp(prefix=f"video_{job_id}_")
    frames_path = temp_dir

    for i, frame in enumerate(frames):
        frame_path = os.path.join(temp_dir, f"frame_{i:05d}.png")

        if isinstance(frame, Image.Image):
            frame.save(frame_path)
        elif isinstance(frame, np.ndarray):
            if frame.dtype == np.float32 or frame.dtype == np.float64:
                frame = (frame * 255).astype(np.uint8)
            if frame.max() <= 1.0:
                frame = (frame * 255).astype(np.uint8)
            img = Image.fromarray(frame)
            img.save(frame_path)
        elif hasattr(frame, 'numpy'):
            arr = frame.cpu().numpy()
            if arr.dtype == np.float32 or arr.dtype == np.float64:
                arr = (arr * 255).astype(np.uint8)
            if len(arr.shape) == 3 and arr.shape[0] in [1, 3, 4]:
                arr = np.transpose(arr, (1, 2, 0))
            img = Image.fromarray(arr)
            img.save(frame_path)
        else:
            logger.warning(f"Unknown frame type: {type(frame)}")

    logger.info(f"Saved {len(frames)} frames to {frames_path}")

    return {
        "generation_success": True,
        "frames_path": frames_path,
        "generation_error": None,
        "generation_metadata": {
            "seed": seed if seed is not None else "random",
            "width": width,
            "height": height,
            "num_frames": len(frames),
            "fps": fps,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_steps,
            "pipeline": "legacy",
        },
    }


def generation_router(state: VideoGraphState) -> Literal["upload", "encode", "error"]:
    """
    Conditional edge function to decide next node.

    For LTX-2: generation_success + encode_success -> upload (skip encode)
    For legacy: generation_success -> encode (need to encode frames)
    Otherwise: error
    """
    if not state.get("generation_success"):
        return "error"

    # If encode_success is already True (LTX-2), skip to upload
    if state.get("encode_success"):
        return "upload"

    # Legacy path needs encoding
    return "encode"
