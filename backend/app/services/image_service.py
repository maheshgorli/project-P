"""
Image persistence service.

Responsibilities
----------------
- Save a numpy image array to disk in backend/images/
- Build structured filenames from event metadata
- List and parse stored image files
- Return serialisable result dicts for API responses

This module has NO knowledge of Sentinel Hub or NASA — it only handles
file I/O and filename conventions.  All imagery arrays come from
sentinel_service.fetch_image().
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ── Directory resolution ──────────────────────────────────────────────────────
# This file is at  backend/app/services/image_service.py
# backend/images/ is three levels up: services/ → app/ → backend/
_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "images"

# ── Filename convention ────────────────────────────────────────────────────────
# Format: {type}_{YYYY-MM-DD}_{HH-MM}_lat{lat}_lon{lon}.png
_FILENAME_RE = re.compile(
    r"^(?P<type>wildfire|storm|satellite|unknown)"
    r"_(?P<date>\d{4}-\d{2}-\d{2})"
    r"_(?P<time>\d{2}-\d{2})"
    r"(?:_lat(?P<lat>-?[\d.]+)_lon(?P<lon>-?[\d.]+))?"
    r"\.png$"
)

_TYPE_LABELS = {
    "wildfire":  "Wildfire",
    "storm":     "Severe Storm",
    "satellite": "Satellite Capture",
    "unknown":   "Unknown",
}


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SavedImage:
    """Metadata record for an image stored on disk."""
    filename:     str
    image_path:   str           # relative path, e.g. "images/wildfire_...png"
    disaster_type: str          # human label
    latitude:     Optional[float]
    longitude:    Optional[float]
    captured_at:  str           # ISO-8601 datetime string
    file_size_bytes: int

    def to_dict(self, base_url: str = "http://127.0.0.1:8000") -> dict:
        return {
            "filename":     self.filename,
            "image_url":    f"{base_url}/{self.image_path}",
            "image_path":   self.image_path,
            "disaster_type": self.disaster_type,
            "location":     (
                f"Lat {self.latitude:.4f}, Lon {self.longitude:.4f}"
                if self.latitude is not None else "Unknown location"
            ),
            "latitude":     self.latitude,
            "longitude":    self.longitude,
            "date":         _format_capture_date(self.captured_at),
            "captured_at":  self.captured_at,
            "file_size_bytes": self.file_size_bytes,
            # AI fields — populated by a future model pipeline
            "prediction":   self.disaster_type,
            "confidence":   0.0,
        }


# ── Service class ─────────────────────────────────────────────────────────────

class _ImageService:
    """Handles saving, listing, and parsing of satellite images on disk."""

    # ── Saving ────────────────────────────────────────────────────────────────

    def save(
        self,
        array: np.ndarray,
        event_type: str = "satellite",
        latitude:  Optional[float] = None,
        longitude: Optional[float] = None,
        filename:  Optional[str]   = None,
    ) -> SavedImage:
        """
        Persist a numpy image array to backend/images/.

        Args:
            array:      uint8 numpy array, shape (H, W, 3).
            event_type: One of "wildfire", "storm", "satellite", "unknown".
            latitude:   Decimal degrees latitude of the image centre.
            longitude:  Decimal degrees longitude of the image centre.
            filename:   Override the auto-generated filename (must end with .png).

        Returns:
            SavedImage with metadata about the saved file.

        Raises:
            ValueError:   if the array cannot be converted to a valid image.
            OSError:      if the file cannot be written.
        """
        _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = self._build_filename(event_type, latitude, longitude)

        full_path = _IMAGES_DIR / filename

        # Ensure array is uint8 before saving
        if array.dtype != np.uint8:
            array = (np.clip(array, 0, 1) * 255).astype(np.uint8)

        try:
            Image.fromarray(array).save(full_path)
        except Exception as exc:
            raise OSError(f"Failed to save image to {full_path}: {exc}") from exc

        file_size = full_path.stat().st_size
        logger.info(
            "Image saved — %s  (%d bytes, shape %s)",
            filename, file_size, array.shape,
        )

        return SavedImage(
            filename=filename,
            image_path=f"images/{filename}",
            disaster_type=_TYPE_LABELS.get(event_type, event_type.title()),
            latitude=latitude,
            longitude=longitude,
            captured_at=datetime.utcnow().isoformat() + "Z",
            file_size_bytes=file_size,
        )

    # ── Deletion ─────────────────────────────────────────────────────────────

    def delete(self, filename: str) -> bool:
        """
        Delete a stored image by filename.

        Args:
            filename: The bare filename (e.g. "wildfire_2026-07-19_13-00_lat17.3850_lon78.4870.png").
                      Path traversal characters are rejected.

        Returns:
            True if the file existed and was deleted, False if it was not found.

        Raises:
            ValueError: if the filename contains path separators or is not a .png.
            OSError:    if the file exists but cannot be deleted.
        """
        # Guard against path traversal
        if "/" in filename or "\\" in filename or ".." in filename:
            raise ValueError(f"Invalid filename — path separators not allowed: {filename!r}")
        if not filename.lower().endswith(".png"):
            raise ValueError(f"Only .png files can be deleted, got: {filename!r}")

        target = _IMAGES_DIR / filename
        if not target.exists():
            logger.warning("delete — file not found: %s", filename)
            return False

        target.unlink()
        logger.info("Image deleted — %s", filename)
        return True

    # ── Listing ───────────────────────────────────────────────────────────────

    def list_images(self) -> list[SavedImage]:
        """
        Return metadata for every recognised .png in the images directory,
        sorted newest-first.
        """
        _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        results = []
        for path in sorted(_IMAGES_DIR.glob("*.png"), reverse=True):
            meta = self._parse_filename(path.name)
            if meta:
                results.append(meta)

        logger.debug("list_images — found %d image(s).", len(results))
        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_filename(
        event_type: str,
        latitude:  Optional[float],
        longitude: Optional[float],
    ) -> str:
        ts = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
        safe_type = event_type.lower() if event_type.lower() in _TYPE_LABELS else "unknown"
        if latitude is not None and longitude is not None:
            return f"{safe_type}_{ts}_lat{latitude:.4f}_lon{longitude:.4f}.png"
        return f"{safe_type}_{ts}.png"

    @staticmethod
    def _parse_filename(filename: str) -> Optional[SavedImage]:
        """Parse a structured filename into a SavedImage, or return None."""
        m = _FILENAME_RE.match(filename)
        if not m:
            return None

        event_type = m.group("type")
        date_str   = m.group("date")
        time_str   = m.group("time").replace("-", ":")
        lat  = float(m.group("lat"))  if m.group("lat")  else None
        lon  = float(m.group("lon"))  if m.group("lon")  else None

        captured_at = f"{date_str}T{time_str}:00Z"

        path = _IMAGES_DIR / filename
        try:
            file_size = path.stat().st_size
        except OSError:
            file_size = 0

        return SavedImage(
            filename=filename,
            image_path=f"images/{filename}",
            disaster_type=_TYPE_LABELS.get(event_type, event_type.title()),
            latitude=lat,
            longitude=lon,
            captured_at=captured_at,
            file_size_bytes=file_size,
        )


# ── Module-level singleton ─────────────────────────────────────────────────────

image_service = _ImageService()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_capture_date(iso: str) -> str:
    """Convert ISO-8601 string to a human-readable label."""
    try:
        dt = datetime.fromisoformat(iso.rstrip("Z"))
        return dt.strftime("%B %d, %Y %H:%M UTC")
    except ValueError:
        return iso

# ── Legacy aliases ─────────────────────────────────────────────────────────────
# Keep the old function signature working so the router doesn't break
# until it's updated to call image_service.save() directly.

DEFAULT_LATITUDE  = 17.3850
DEFAULT_LONGITUDE = 78.4867

def fetch_satellite_image(
    latitude:        float = DEFAULT_LATITUDE,
    longitude:       float = DEFAULT_LONGITUDE,
    bbox_size:       float = 0.05,
    output_filename: Optional[str] = None,
    date_from:       str = "2024-01-01",
    date_to:         str = "2024-06-30",
    resolution:      int = 60,
) -> dict:
    """
    Legacy wrapper: fetch a Sentinel-2 image and save it.

    Prefer calling sentinel_service.fetch_image() + image_service.save() directly.
    """
    from app.services.sentinel_service import sentinel_service
    result = sentinel_service.fetch_image(
        latitude=latitude,
        longitude=longitude,
        date_from=date_from,
        date_to=date_to,
        resolution=resolution,
        bbox_size=bbox_size,
    )
    saved = image_service.save(
        array=result.array,
        event_type="satellite",
        latitude=latitude,
        longitude=longitude,
        filename=output_filename,
    )
    return {
        "image_path":        saved.image_path,
        "filename":          saved.filename,
        "latitude":          latitude,
        "longitude":         longitude,
        "bbox":              result.meta.bbox,
        "resolution_meters": result.meta.resolution_meters,
        "image_size_pixels": result.meta.image_size_pixels,
        "time_interval":     [date_from, date_to],
        "data_collection":   result.meta.data_collection,
        "file_size_bytes":   saved.file_size_bytes,
    }
