"""
Gallery router — serves metadata for all images stored in backend/images/.

Each image filename encodes: {type}_{date}_{time}.png
Example: wildfire_2026-07-18_14-30.png
"""

import os
import re
from datetime import datetime
from fastapi import APIRouter

router = APIRouter()

# Resolved once at import time; same logic as main.py IMAGES_DIR
_IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "images",
)

# Regex to parse structured filenames produced by /monitor
_FILENAME_RE = re.compile(
    r"^(?P<type>wildfire|storm|satellite)"
    r"_(?P<date>\d{4}-\d{2}-\d{2})"
    r"_(?P<time>\d{2}-\d{2})"
    r"(?:_lat(?P<lat>-?[\d.]+)_lon(?P<lon>-?[\d.]+))?"
    r"\.png$"
)

_DISASTER_LABELS = {
    "wildfire": "Wildfire",
    "storm": "Severe Storm",
    "satellite": "Satellite Capture",
}


def _parse_image_meta(filename: str, base_url: str = "http://127.0.0.1:8000") -> dict | None:
    """Return metadata dict for a valid image filename, or None if unrecognised."""
    m = _FILENAME_RE.match(filename)
    if not m:
        return None

    disaster_type = m.group("type")
    date_str = m.group("date")
    time_str = m.group("time").replace("-", ":")
    lat = float(m.group("lat")) if m.group("lat") else None
    lon = float(m.group("lon")) if m.group("lon") else None

    # Build a human-readable capture datetime
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        capture_date = dt.strftime("%B %d, %Y %H:%M UTC")
    except ValueError:
        capture_date = f"{date_str} {time_str} UTC"

    location = (
        f"Lat {lat:.4f}, Lon {lon:.4f}" if lat is not None else "Unknown location"
    )

    return {
        "filename": filename,
        "image_url": f"{base_url}/images/{filename}",
        "location": location,
        "date": capture_date,
        "disaster_type": _DISASTER_LABELS.get(disaster_type, disaster_type.title()),
        # Placeholder values — replace with real AI model output in a future phase
        "prediction": _DISASTER_LABELS.get(disaster_type, disaster_type.title()),
        "confidence": 0.0,
    }


@router.get("/gallery")
def get_gallery():
    """Return metadata for every image stored in backend/images/."""
    os.makedirs(_IMAGES_DIR, exist_ok=True)

    images = []
    for fname in sorted(os.listdir(_IMAGES_DIR), reverse=True):
        if not fname.lower().endswith(".png"):
            continue
        meta = _parse_image_meta(fname)
        if meta:
            images.append(meta)

    return images
