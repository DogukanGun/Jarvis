import base64

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.services import FaceRecognitionService

face_router = APIRouter()


class ImagePayload(BaseModel):
    image: str  # base64-encoded JPEG


def _decode_base64_image(image_b64: str) -> bytes:
    """Strip optional data-URI prefix and decode base64 to bytes."""
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    return base64.b64decode(image_b64)


@face_router.get("/admin/exists")
async def is_admin_exists():
    return {"exists": FaceRecognitionService.admin_exists()}


@face_router.post("/admin/enroll")
async def register_face(payload: ImagePayload):
    try:
        image_bytes = _decode_base64_image(payload.image)
        result = FaceRecognitionService.enroll_admin(image_bytes=image_bytes)
        return {
            "success": True,
            "message": "Face registered successfully",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@face_router.post("/admin/verify")
async def validate_admin_face(payload: ImagePayload):
    try:
        image_bytes = _decode_base64_image(payload.image)
        result = FaceRecognitionService.is_admin(image_bytes=image_bytes)
        return {
            "success": True,
            "message": "Verification completed",
            "data": result,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))