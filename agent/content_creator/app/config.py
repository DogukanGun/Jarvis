"""
Configuration for Content Creator Media Rendering Pipeline.

Environment-based configuration for Kafka, MinIO, and model settings.
"""
import os


class Config:
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_GROUP_ID: str = os.getenv("KAFKA_GROUP_ID", "content-creator")

    # Kafka topics
    KAFKA_TOPIC_REQUESTS: str = os.getenv("KAFKA_TOPIC_REQUESTS", "media.render.requests")
    KAFKA_TOPIC_VIDEO_REQUESTS: str = os.getenv("KAFKA_TOPIC_VIDEO_REQUESTS", "media.render.video.requests")
    KAFKA_TOPIC_IMAGE_PROMPT_REQUESTS: str = os.getenv("KAFKA_TOPIC_IMAGE_PROMPT_REQUESTS", "media.render.image.prompt.requests")
    KAFKA_TOPIC_IMAGE_REFERENCE_REQUESTS: str = os.getenv("KAFKA_TOPIC_IMAGE_REFERENCE_REQUESTS", "media.render.image.reference.requests")
    KAFKA_TOPIC_IMAGE_EDIT_REQUESTS: str = os.getenv("KAFKA_TOPIC_IMAGE_EDIT_REQUESTS", "media.render.image.edit.requests")
    KAFKA_TOPIC_RESULTS: str = os.getenv("KAFKA_TOPIC_RESULTS", "media.render.results")

    # MinIO/S3 settings
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "media-renders")
    MINIO_USE_SSL: bool = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
    MINIO_PUBLIC_URL: str = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")

    # Model settings
    MODEL_CACHE_DIR: str = os.getenv("MODEL_CACHE_DIR", "/models")

    # Image generation models (these work on Mac MPS without auth)
    # Options: "CompVis/stable-diffusion-v1-4", "segmind/SSD-1B", "stabilityai/stable-diffusion-2-1" (needs auth)
    QWEN_IMAGE_MODEL: str = os.getenv("IMAGE_MODEL", "CompVis/stable-diffusion-v1-4")

    # Image editing model (same as image model, used for img2img)
    QWEN_IMAGE_EDIT_MODEL: str = os.getenv("IMAGE_EDIT_MODEL", "CompVis/stable-diffusion-v1-4")

    # Video generation model
    # Options: "Lightricks/LTX-2", "damo-vilab/text-to-video-ms-1.7b", "cerspense/zeroscope_v2_576w"
    LTX_VIDEO_MODEL: str = os.getenv("VIDEO_MODEL", "Lightricks/LTX-2")

    # LTX-2 Model Paths (auto-downloaded to MODEL_CACHE_DIR if not specified)
    LTX_CHECKPOINT_PATH: str = os.getenv("LTX_CHECKPOINT_PATH", "")
    LTX_DISTILLED_LORA_PATH: str = os.getenv("LTX_DISTILLED_LORA_PATH", "")
    LTX_DISTILLED_LORA_STRENGTH: float = float(os.getenv("LTX_DISTILLED_LORA_STRENGTH", "0.6"))
    LTX_SPATIAL_UPSAMPLER_PATH: str = os.getenv("LTX_SPATIAL_UPSAMPLER_PATH", "")
    LTX_GEMMA_ROOT: str = os.getenv("LTX_GEMMA_ROOT", "")
    LTX_ENABLE_FP8: bool = os.getenv("LTX_ENABLE_FP8", "true").lower() == "true"

    # LTX-2 Generation Defaults (optimized for two-stage)
    LTX_DEFAULT_HEIGHT: int = int(os.getenv("LTX_DEFAULT_HEIGHT", "1024"))
    LTX_DEFAULT_WIDTH: int = int(os.getenv("LTX_DEFAULT_WIDTH", "1536"))
    LTX_DEFAULT_NUM_FRAMES: int = int(os.getenv("LTX_DEFAULT_NUM_FRAMES", "121"))
    LTX_DEFAULT_FRAME_RATE: float = float(os.getenv("LTX_DEFAULT_FRAME_RATE", "24.0"))
    LTX_DEFAULT_CFG_GUIDANCE_SCALE: float = float(os.getenv("LTX_DEFAULT_CFG_GUIDANCE_SCALE", "4.0"))
    LTX_DEFAULT_NUM_INFERENCE_STEPS: int = int(os.getenv("LTX_DEFAULT_NUM_INFERENCE_STEPS", "40"))

    # Generation defaults
    DEFAULT_IMAGE_WIDTH: int = int(os.getenv("DEFAULT_IMAGE_WIDTH", "1024"))
    DEFAULT_IMAGE_HEIGHT: int = int(os.getenv("DEFAULT_IMAGE_HEIGHT", "1024"))
    DEFAULT_VIDEO_WIDTH: int = int(os.getenv("DEFAULT_VIDEO_WIDTH", "768"))
    DEFAULT_VIDEO_HEIGHT: int = int(os.getenv("DEFAULT_VIDEO_HEIGHT", "512"))
    DEFAULT_VIDEO_DURATION: float = float(os.getenv("DEFAULT_VIDEO_DURATION", "6.0"))
    DEFAULT_VIDEO_FPS: int = int(os.getenv("DEFAULT_VIDEO_FPS", "24"))

    # Generation parameters
    DEFAULT_GUIDANCE_SCALE: float = float(os.getenv("DEFAULT_GUIDANCE_SCALE", "7.5"))
    DEFAULT_NUM_INFERENCE_STEPS: int = int(os.getenv("DEFAULT_NUM_INFERENCE_STEPS", "50"))

    # Worker settings
    WORKER_TYPE: str = os.getenv("WORKER_TYPE", "router")  # router, video, image_prompt, image_edit
    GPU_DEVICE: str = os.getenv("GPU_DEVICE", "cuda:0")

    # HTTP client settings (for downloading reference images)
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))


config = Config()
