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


def _fetch_events_by_category(category_id: str) -> list:
    """Fetch EONET events filtered by category_id. Returns [] on any fetch/parse failure."""
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
                results.append({
                    "title": event.get("title"),
                    "event_id": event.get("id"),
                    "category": category.get("title"),
                    "coordinates": event.get("geometry", [{}])[0].get("coordinates"),
                })

    return results


@router.get("/satellite")
def satellite():
    response = requests.get(NASA_URL, timeout=10)

    return {
        "status": response.status_code
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
    latitude: float = 17.3850,
    longitude: float = 78.4867,
):
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


@router.get("/wildfires")
def get_wildfires():
    return _fetch_events_by_category("wildfires")


@router.get("/storms")
def get_storms():
    return _fetch_events_by_category("severeStorms")
