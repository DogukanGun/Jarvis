"""
Model Client for HuggingFace Models.

Handles loading, cloning, and caching of various Hugging Face models.
Supports CUDA, MPS (Apple Silicon), and CPU.
"""
import logging
import os
from typing import Optional, Any, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


def _download_ltx2_models(cache_dir: str) -> Dict[str, str]:
    """
    Auto-download LTX-2 models from HuggingFace Hub.
    Files are cached locally - downloads only happen once.

    Args:
        cache_dir: Directory to cache downloaded models

    Returns:
        Dictionary with paths to downloaded model files
    """
    from huggingface_hub import hf_hub_download, snapshot_download

    paths = {}

    logger.info("Downloading LTX-2 models (will use cache if already downloaded)...")

    # Download checkpoint (FP8 version for lower memory)
    # hf_hub_download checks cache first - skips if exists
    logger.info("Downloading LTX-2 checkpoint (FP8)...")
    paths["checkpoint"] = hf_hub_download(
        repo_id="Lightricks/LTX-2",
        filename="ltx-2-19b-dev-fp8.safetensors",
        cache_dir=cache_dir,
        resume_download=True,
    )

    # Download spatial upsampler
    logger.info("Downloading LTX-2 spatial upsampler...")
    paths["spatial_upsampler"] = hf_hub_download(
        repo_id="Lightricks/LTX-2",
        filename="ltx-2-spatial-upscaler-x2-1.0.safetensors",
        cache_dir=cache_dir,
        resume_download=True,
    )

    # Download distilled LoRA
    logger.info("Downloading LTX-2 distilled LoRA...")
    paths["distilled_lora"] = hf_hub_download(
        repo_id="Lightricks/LTX-2",
        filename="ltx-2-19b-distilled-lora-384.safetensors",
        cache_dir=cache_dir,
        resume_download=True,
    )

    # Download Gemma text encoder (full directory)
    logger.info("Downloading Gemma text encoder...")
    paths["gemma_root"] = snapshot_download(
        repo_id="google/gemma-3-12b-it-qat-q4_0-unquantized",
        cache_dir=cache_dir,
        resume_download=True,
    )

    logger.info("All LTX-2 models downloaded successfully")
    return paths


def get_best_device() -> str:
    """
    Auto-detect the best available device.

    Priority: CUDA > MPS > CPU
    """
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
            return "mps"
        else:
            return "cpu"
    except ImportError:
        return "cpu"


def get_torch_dtype(device: str):
    """Get appropriate torch dtype for the device."""
    try:
        import torch

        if device == "cuda":
            return torch.float16
        elif device == "mps":
            # MPS works best with float32 for many models, but some support float16
            return torch.float32
        else:
            return torch.float32
    except ImportError:
        return None


class ModelClient:
    """
    Client for loading and managing HuggingFace models.

    Handles:
    - Lazy loading of models
    - Auto device detection (CUDA/MPS/CPU)
    - Model caching
    """

    def __init__(
        self,
        cache_dir: str = None,
        device: str = None,
    ):
        """
        Initialize model client.

        Args:
            cache_dir: Directory for model cache (None for default HF cache)
            device: Device to load models on (None for auto-detect)
        """
        self.cache_dir = cache_dir if cache_dir and cache_dir != "/models" else None
        self.device = device if device and device != "cuda:0" else get_best_device()
        self._models: Dict[str, Any] = {}

        logger.info(f"ModelClient initialized - device: {self.device}, cache: {self.cache_dir or 'default'}")

    def load_image_pipeline(self, model_id: str) -> Any:
        """
        Load a text-to-image pipeline.

        Args:
            model_id: HuggingFace model ID

        Returns:
            Loaded pipeline
        """
        cache_key = f"image:{model_id}"
        if cache_key in self._models:
            return self._models[cache_key]

        try:
            import torch
            from diffusers import AutoPipelineForText2Image

            logger.info(f"Loading image pipeline: {model_id}")
            logger.info(f"Device: {self.device}")

            dtype = get_torch_dtype(self.device)
            logger.info(f"Using dtype: {dtype}")

            # Load pipeline
            pipeline = AutoPipelineForText2Image.from_pretrained(
                model_id,
                torch_dtype=dtype,
                cache_dir=self.cache_dir,
            )

            # Move to device
            pipeline = pipeline.to(self.device)
            logger.info(f"Model loaded on {self.device}")

            # Enable memory optimizations
            if self.device == "cuda":
                try:
                    pipeline.enable_model_cpu_offload()
                except Exception:
                    pass

            self._models[cache_key] = pipeline
            return pipeline

        except ImportError as e:
            logger.error(f"Missing dependency for image pipeline: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load image pipeline {model_id}: {e}")
            raise

    def load_image_edit_pipeline(self, model_id: str) -> Any:
        """
        Load an image-to-image / editing pipeline.

        Args:
            model_id: HuggingFace model ID

        Returns:
            Loaded pipeline
        """
        cache_key = f"image_edit:{model_id}"
        if cache_key in self._models:
            return self._models[cache_key]

        try:
            import torch
            from diffusers import AutoPipelineForImage2Image

            logger.info(f"Loading image edit pipeline: {model_id}")
            logger.info(f"Device: {self.device}")

            dtype = get_torch_dtype(self.device)

            pipeline = AutoPipelineForImage2Image.from_pretrained(
                model_id,
                torch_dtype=dtype,
                cache_dir=self.cache_dir,
            )

            pipeline = pipeline.to(self.device)
            logger.info(f"Model loaded on {self.device}")

            self._models[cache_key] = pipeline
            return pipeline

        except ImportError as e:
            logger.error(f"Missing dependency for image edit pipeline: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load image edit pipeline {model_id}: {e}")
            raise

    def load_video_pipeline(self, model_id: str) -> Any:
        """
        Load a video generation pipeline.

        Args:
            model_id: HuggingFace model ID

        Returns:
            Loaded pipeline
        """
        cache_key = f"video:{model_id}"
        if cache_key in self._models:
            return self._models[cache_key]

        try:
            import torch

            logger.info(f"Loading video pipeline: {model_id}")
            logger.info(f"Device: {self.device}")

            dtype = get_torch_dtype(self.device)

            # Try different pipeline types based on model
            if "animatediff" in model_id.lower():
                from diffusers import AnimateDiffPipeline, MotionAdapter, DDIMScheduler

                adapter = MotionAdapter.from_pretrained(
                    "guoyww/animatediff-motion-adapter-v1-5-2",
                    torch_dtype=dtype,
                )
                pipeline = AnimateDiffPipeline.from_pretrained(
                    model_id,
                    motion_adapter=adapter,
                    torch_dtype=dtype,
                    cache_dir=self.cache_dir,
                )
                pipeline.scheduler = DDIMScheduler.from_config(
                    pipeline.scheduler.config,
                    beta_schedule="linear",
                    steps_offset=1,
                    clip_sample=False,
                )
            elif "text-to-video" in model_id.lower() or "zeroscope" in model_id.lower():
                from diffusers import DiffusionPipeline
                pipeline = DiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    cache_dir=self.cache_dir,
                )
            else:
                # Try generic text-to-video
                from diffusers import DiffusionPipeline
                pipeline = DiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    cache_dir=self.cache_dir,
                )

            pipeline = pipeline.to(self.device)
            logger.info(f"Video model loaded on {self.device}")

            self._models[cache_key] = pipeline
            return pipeline

        except ImportError as e:
            logger.error(f"Missing dependency for video pipeline: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load video pipeline {model_id}: {e}")
            raise

    def load_ltx2_pipeline(self) -> Any:
        """
        Load the LTX-2 TI2VidTwoStagesPipeline with auto-download and caching.

        Models are downloaded from HuggingFace Hub on first use and cached locally.
        The pipeline instance is also cached in memory for subsequent calls.

        Returns:
            TI2VidTwoStagesPipeline instance
        """
        cache_key = "ltx2:two_stage"
        if cache_key in self._models:
            logger.info("Returning cached LTX-2 pipeline")
            return self._models[cache_key]

        try:
            from app.config import config

            logger.info("Loading LTX-2 TI2VidTwoStagesPipeline...")

            # Determine model paths - use config if provided, otherwise auto-download
            cache_dir = self.cache_dir or os.path.expanduser("~/.cache/huggingface")

            if config.LTX_CHECKPOINT_PATH and config.LTX_DISTILLED_LORA_PATH and \
               config.LTX_SPATIAL_UPSAMPLER_PATH and config.LTX_GEMMA_ROOT:
                # Use paths from config
                logger.info("Using model paths from configuration")
                model_paths = {
                    "checkpoint": config.LTX_CHECKPOINT_PATH,
                    "distilled_lora": config.LTX_DISTILLED_LORA_PATH,
                    "spatial_upsampler": config.LTX_SPATIAL_UPSAMPLER_PATH,
                    "gemma_root": config.LTX_GEMMA_ROOT,
                }
            else:
                # Auto-download models
                logger.info("Auto-downloading LTX-2 models from HuggingFace...")
                model_paths = _download_ltx2_models(cache_dir)

            # Import LTX-2 pipeline components
            from ltx_pipelines import TI2VidTwoStagesPipeline
            from ltx_core.loader import LoraPathStrengthAndSDOps, LTXV_LORA_COMFY_RENAMING_MAP

            # Create distilled LoRA specification
            distilled_lora = [
                LoraPathStrengthAndSDOps(
                    path=model_paths["distilled_lora"],
                    strength=config.LTX_DISTILLED_LORA_STRENGTH,
                    sd_key_value_op=LTXV_LORA_COMFY_RENAMING_MAP,
                )
            ]

            # Create pipeline
            logger.info(f"Initializing TI2VidTwoStagesPipeline on {self.device}...")
            pipeline = TI2VidTwoStagesPipeline(
                checkpoint_path=model_paths["checkpoint"],
                distilled_lora=distilled_lora,
                spatial_upsampler_path=model_paths["spatial_upsampler"],
                gemma_root=model_paths["gemma_root"],
                loras=[],  # No additional LoRAs by default
                device=self.device,
                fp8transformer=config.LTX_ENABLE_FP8,
            )

            logger.info("LTX-2 pipeline loaded successfully")
            self._models[cache_key] = pipeline
            return pipeline

        except ImportError as e:
            logger.error(f"Missing LTX-2 dependency: {e}")
            logger.error("Install with: pip install -e ./LTX-2/packages/ltx-core && pip install -e ./LTX-2/packages/ltx-pipelines")
            raise
        except Exception as e:
            logger.error(f"Failed to load LTX-2 pipeline: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def unload_model(self, cache_key: str):
        """Unload a model to free memory."""
        if cache_key in self._models:
            del self._models[cache_key]
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                elif torch.backends.mps.is_available():
                    torch.mps.empty_cache()
            except Exception:
                pass
            logger.info(f"Unloaded model: {cache_key}")

    def clone_model(self, model_id: str, model_type: str = "auto", cache_dir: str = None) -> str:
        """
        Clone/download a model from Hugging Face Hub to local cache.

        Args:
            model_id: HuggingFace model ID (e.g., 'runwayml/stable-diffusion-v1-5')
            model_type: Type of model ('text', 'image', 'audio', 'video', 'transformer', 'auto')
            cache_dir: Directory to store the cloned model (uses default if None)

        Returns:
            Path to the cloned model directory
        """
        try:
            from huggingface_hub import snapshot_download
            import torch

            logger.info(f"Cloning model: {model_id}")

            # Determine cache directory
            target_dir = cache_dir or self.cache_dir

            # Download the model snapshot
            model_path = snapshot_download(
                repo_id=model_id,
                cache_dir=target_dir,
                resume_download=True,
                tqdm_class=None,
            )

            logger.info(f"Model cloned successfully to: {model_path}")
            return model_path

        except ImportError:
            logger.error("huggingface_hub package is not installed. Install it with: pip install huggingface_hub")
            raise
        except Exception as e:
            logger.error(f"Failed to clone model {model_id}: {e}")
            raise

    def load_local_model(self, model_path: str, model_type: str = "auto"):
        """
        Load a model from a local path.

        Args:
            model_path: Path to the local model directory
            model_type: Type of model ('text', 'image', 'audio', 'video', 'transformer', 'auto')

        Returns:
            Loaded model
        """
        try:
            import torch
            from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM, \
                AutoModelForSequenceClassification, AutoModelForQuestionAnswering
            from diffusers import DiffusionPipeline

            logger.info(f"Loading model from local path: {model_path}")

            # Determine model type if auto-detect
            if model_type == "auto":
                # Try to infer from config or model files
                config_path = os.path.join(model_path, "config.json")
                if os.path.exists(config_path):
                    import json
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    arch = config.get("architectures", [])
                    if arch:
                        arch_str = str(arch[0]).lower()
                        if "forcausallm" in arch_str or "gpt" in arch_str or "llama" in arch_str:
                            model_type = "text-generation"
                        elif "forsequenceclassification" in arch_str:
                            model_type = "text-classification"
                        elif "fordiffusion" in arch_str or "unet" in arch_str:
                            model_type = "image"

            # Load based on model type
            if model_type in ["text-generation", "text", "language"]:
                try:
                    model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=get_torch_dtype(self.device))
                    tokenizer = AutoTokenizer.from_pretrained(model_path)
                    model = model.to(self.device)
                    return {"model": model, "tokenizer": tokenizer}
                except:
                    model = AutoModel.from_pretrained(model_path, torch_dtype=get_torch_dtype(self.device))
                    tokenizer = AutoTokenizer.from_pretrained(model_path)
                    model = model.to(self.device)
                    return {"model": model, "tokenizer": tokenizer}
            elif model_type in ["image", "diffusion"]:
                pipeline = DiffusionPipeline.from_pretrained(model_path, torch_dtype=get_torch_dtype(self.device))
                pipeline = pipeline.to(self.device)
                return pipeline
            elif model_type in ["text-classification", "sentiment", "qa"]:
                model = AutoModelForSequenceClassification.from_pretrained(model_path)
                tokenizer = AutoTokenizer.from_pretrained(model_path)
                model = model.to(self.device)
                return {"model": model, "tokenizer": tokenizer}
            else:
                # Default to general transformer model
                model = AutoModel.from_pretrained(model_path, torch_dtype=get_torch_dtype(self.device))
                tokenizer = AutoTokenizer.from_pretrained(model_path)
                model = model.to(self.device)
                return {"model": model, "tokenizer": tokenizer}

        except Exception as e:
            logger.error(f"Failed to load local model from {model_path}: {e}")
            raise

    def unload_all(self):
        """Unload all models."""
        keys = list(self._models.keys())
        for key in keys:
            self.unload_model(key)


# Singleton instances
_image_model: Optional[Any] = None
_image_edit_model: Optional[Any] = None
_video_model: Optional[Any] = None
_model_client: Optional[ModelClient] = None


def _get_client() -> ModelClient:
    """Get singleton model client."""
    global _model_client
    if _model_client is None:
        from app.config import config
        _model_client = ModelClient(
            cache_dir=config.MODEL_CACHE_DIR,
            device=None,  # Auto-detect
        )
    return _model_client


def get_image_model() -> Any:
    """Get the text-to-image model."""
    global _image_model
    if _image_model is None:
        from app.config import config
        client = _get_client()
        _image_model = client.load_image_pipeline(config.QWEN_IMAGE_MODEL)
    return _image_model


def get_image_edit_model() -> Any:
    """Get the image editing model."""
    global _image_edit_model
    if _image_edit_model is None:
        from app.config import config
        client = _get_client()
        _image_edit_model = client.load_image_edit_pipeline(config.QWEN_IMAGE_EDIT_MODEL)
    return _image_edit_model


def get_video_model() -> Any:
    """Get the video generation model."""
    global _video_model
    if _video_model is None:
        from app.config import config
        client = _get_client()
        # Use LTX-2 TwoStages pipeline if LTX-2 is specified
        if "ltx-2" in config.LTX_VIDEO_MODEL.lower():
            _video_model = client.load_ltx2_pipeline()
        else:
            _video_model = client.load_video_pipeline(config.LTX_VIDEO_MODEL)
    return _video_model
