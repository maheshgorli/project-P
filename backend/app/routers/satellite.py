from fastapi import APIRouter
import requests
from backend.app.services.sentinel_service import get_config

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
    try:
        config = get_config()
    except ValueError as e:
        return {"authenticated": False, "error": str(e)}
    return {
        "authenticated": True,
        "client_id": config.sh_client_id[:10] + "...",
    }


@router.get("/wildfires")
def get_wildfires():
    return _fetch_events_by_category("wildfires")


@router.get("/storms")
def get_storms():
    return _fetch_events_by_category("severeStorms")
