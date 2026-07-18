"""
Satellite router — NASA EONET events + Sentinel Hub image capture.

Endpoints
---------
GET /satellite          — raw EONET status check
GET /wildfires          — active wildfire events
GET /storms             — active severe-storm events
GET /monitor            — fetch events + download Sentinel images for each one
GET /satellite-image    — download a single image by lat/lon
GET /sentinel-test      — OAuth credential smoke-test
"""

from datetime import datetime
from fastapi import APIRouter
import requests

try:
    from app.services.sentinel_service import get_config
    from app.services.image_service import (
        fetch_satellite_image,
        DEFAULT_LATITUDE,
        DEFAULT_LONGITUDE,
    )
    SENTINEL_AVAILABLE = True
except ImportError as e:
    SENTINEL_AVAILABLE = False
    _SENTINEL_IMPORT_ERROR = str(e)

router = APIRouter()

NASA_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_events_by_category(category_id: str) -> list:
    """Fetch EONET events filtered by category_id. Returns [] on any failure."""
    try:
        response = requests.get(NASA_URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[satellite] Failed to fetch NASA EONET data: {e}")
        return []

    data = response.json()
    results = []

    for event in data.get("events", []):
        for category in event.get("categories", []):
            if category.get("id") == category_id:
                coords = event.get("geometry", [{}])[0].get("coordinates")
                results.append({
                    "title": event.get("title"),
                    "event_id": event.get("id"),
                    "category": category.get("title"),
                    "coordinates": coords,
                })

    return results


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/satellite")
def satellite():
    response = requests.get(NASA_URL, timeout=10)
    return {"status": response.status_code}


@router.get("/wildfires")
def get_wildfires():
    return _fetch_events_by_category("wildfires")


@router.get("/storms")
def get_storms():
    return _fetch_events_by_category("severeStorms")


@router.get("/monitor")
def monitor():
    """
    Fetch active wildfire + storm events from NASA EONET, then download a
    Sentinel-2 image for each event that has valid coordinates.

    Returns a summary of all events and which images were successfully saved.
    """
    wildfires = _fetch_events_by_category("wildfires")
    storms = _fetch_events_by_category("severeStorms")
    all_events = [("wildfire", e) for e in wildfires] + [("storm", e) for e in storms]

    downloaded = []
    failed = []

    if SENTINEL_AVAILABLE:
        for event_type, event in all_events:
            coords = event.get("coordinates")
            if not coords or len(coords) < 2:
                continue  # skip events without valid coordinates

            lon, lat = float(coords[0]), float(coords[1])
            timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
            filename = f"{event_type}_{timestamp}_lat{lat:.4f}_lon{lon:.4f}.png"

            try:
                details = fetch_satellite_image(
                    latitude=lat,
                    longitude=lon,
                    output_filename=filename,
                )
                downloaded.append({
                    "event_id": event.get("event_id"),
                    "title": event.get("title"),
                    "type": event_type,
                    "image_url": f"http://127.0.0.1:8000/{details['image_path']}",
                    "filename": details["filename"],
                })
            except RuntimeError as e:
                failed.append({
                    "event_id": event.get("event_id"),
                    "title": event.get("title"),
                    "error": str(e),
                })
    else:
        # Sentinel not available — still return event stats
        failed = [
            {"error": f"Sentinel Hub unavailable: {_SENTINEL_IMPORT_ERROR}"}
        ]

    return {
        "success": True,
        "wildfires": len(wildfires),
        "storms": len(storms),
        "total_events": len(all_events),
        "images_downloaded": len(downloaded),
        "images_failed": len(failed),
        "downloaded": downloaded,
        "failed": failed,
    }


@router.get("/sentinel-test")
def sentinel_test():
    if not SENTINEL_AVAILABLE:
        return {
            "authenticated": False,
            "error": f"Sentinel Hub dependencies not installed: {_SENTINEL_IMPORT_ERROR}",
        }
    try:
        config = get_config()
    except ValueError as e:
        return {"authenticated": False, "error": str(e)}
    return {
        "authenticated": True,
        "client_id": config.sh_client_id[:10] + "...",
    }


@router.get("/satellite-image")
def satellite_image(
    latitude: float = DEFAULT_LATITUDE if SENTINEL_AVAILABLE else 17.3850,
    longitude: float = DEFAULT_LONGITUDE if SENTINEL_AVAILABLE else 78.4867,
):
    """Download a single Sentinel-2 image for the given coordinates."""
    if not SENTINEL_AVAILABLE:
        return {
            "success": False,
            "error": f"Sentinel Hub dependencies not installed: {_SENTINEL_IMPORT_ERROR}",
        }
    try:
        details = fetch_satellite_image(latitude, longitude)
    except RuntimeError as e:
        return {"success": False, "error": str(e)}
    return {
        "success": True,
        "image_url": f"http://127.0.0.1:8000/{details['image_path']}",
        **details,
    }
