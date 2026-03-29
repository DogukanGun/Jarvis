"""Face API — FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.services.face_service import admin_exists, delete_admin, enroll_admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Jarvis Face API", description="Admin face enrollment and verification", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EnrollRequest(BaseModel):
    image: str  # base64-encoded JPEG or PNG


@app.get("/health")
def health():
    return {"status": "healthy", "service": "face-api"}


@app.get("/api/admin/exists")
def get_admin_exists():
    return {"exists": admin_exists()}


@app.post("/api/admin/enroll")
def post_enroll_admin(body: EnrollRequest):
    return enroll_admin(body.image)


@app.delete("/api/admin")
def delete_admin_route():
    return delete_admin()
