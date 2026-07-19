"""
Gallery router.

Delegates all image listing to image_service — no filesystem logic here.
"""

import logging
from fastapi import APIRouter

from app.services.image_service import image_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/gallery")
def get_gallery():
    """Return metadata for every stored image in backend/images/, newest first."""
    images = image_service.list_images()
    return [img.to_dict() for img in images]
