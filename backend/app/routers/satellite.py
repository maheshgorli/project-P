"""
Satellite router.

All business logic lives in the service layer:
  - nasa_service    → EONET event fetching + formatting
  - sentinel_service → Sentinel Hub auth + imagery
  - image_service   → file persistence

This router is responsible only for:
  - Declaring HTTP endpoints and their parameters
  - Calling the right service methods
  - Shaping the HTTP response
  - Translating service exceptions into appropriate HTTP responses

Endpoints
---------
GET /satellite          — EONET API health check
GET /wildfires          — active wildfire events
GET /storms             — active severe-storm events
GET /monitor            — fetch events + download a Sentinel image per event
GET /satellite-image    — download a single image by lat/lon + date range
GET /sentinel-test      — Sentinel Hub OAuth smoke-test
GET /auth/token         — return (redacted) current OAuth token info
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.services.nasa_service import nasa_service, NasaServiceError
from app.services.sentinel_service import (
    sentinel_service,
    SentinelServiceError,
    AuthenticationError,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_DATE_FROM,
    DEFAULT_DATE_TO,
    DEFAULT_RESOLUTION,
    DEFAULT_BBOX_SIZE,
)
from app.services.image_service import image_service
from app.services.token_service import token_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── NASA / EONET endpoints ────────────────────────────────────────────────────

@router.get("/satellite")
def satellite():
    """EONET API reachability check."""
    return nasa_service.check_api_status()


@router.get("/wildfires")
def get_wildfires(
    days: int = Query(default=None, ge=1, le=365, description="Restrict to events within the last N days"),
):
    """Return active wildfire events from NASA EONET."""
    try:
        events = nasa_service.fetch_wildfires(days=days)
    except NasaServiceError as exc:
        logger.error("Wildfire fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    return [e.to_dict() for e in events]


@router.get("/storms")
def get_storms(
    days: int = Query(default=None, ge=1, le=365, description="Restrict to events within the last N days"),
):
    """Return active severe-storm events from NASA EONET."""
    try:
        events = nasa_service.fetch_storms(days=days)
    except NasaServiceError as exc:
        logger.error("Storm fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    return [e.to_dict() for e in events]


# ── Sentinel Hub endpoints ────────────────────────────────────────────────────

@router.get("/sentinel-test")
def sentinel_test():
    """Validate Sentinel Hub OAuth credentials."""
    try:
        token = sentinel_service.get_token()
    except EnvironmentError as exc:
        return {"authenticated": False, "error": str(exc)}
    except AuthenticationError as exc:
        return {"authenticated": False, "error": str(exc)}
    return {
        "authenticated":   True,
        "token_type":      token.token_type,
        "expires_in":      token.expires_in,
        "seconds_remaining": round(token.seconds_remaining),
    }


@router.get("/auth/token")
def auth_token():
    """
    Return the current (cached) CDSE OAuth token summary.

    The access_token value is redacted — only the first 10 characters
    are shown.  The full token is used internally.
    """
    try:
        token = token_service.get_token()
    except EnvironmentError as exc:
        return {"success": False, "error": str(exc)}
    except AuthenticationError as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, **token.redacted_summary()}


@router.get("/satellite-image")
def satellite_image(
    latitude:  float = Query(default=DEFAULT_LATITUDE,  ge=-90,   le=90,   description="Centre latitude"),
    longitude: float = Query(default=DEFAULT_LONGITUDE, ge=-180,  le=180,  description="Centre longitude"),
    date_from: str   = Query(default=DEFAULT_DATE_FROM,            description="Start date YYYY-MM-DD"),
    date_to:   str   = Query(default=DEFAULT_DATE_TO,              description="End date   YYYY-MM-DD"),
    resolution: int  = Query(default=DEFAULT_RESOLUTION, ge=10, le=1000,   description="Metres per pixel"),
    bbox_size: float = Query(default=DEFAULT_BBOX_SIZE,  gt=0,  le=5.0,    description="BBox half-extent in degrees"),
):
    """
    Download a single Sentinel-2 true-colour image and save it to disk.

    Returns the image URL and full metadata.
    """
    try:
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (AuthenticationError, EnvironmentError) as exc:
        return {"success": False, "error": str(exc)}
    except SentinelServiceError as exc:
        return {"success": False, "error": str(exc)}

    return {
        "success":           True,
        "image_url":         f"http://127.0.0.1:8000/{saved.image_path}",
        **saved.to_dict(),
        "bbox":              result.meta.bbox,
        "resolution_meters": result.meta.resolution_meters,
        "image_size_pixels": result.meta.image_size_pixels,
        "date_from":         date_from,
        "date_to":           date_to,
        "data_collection":   result.meta.data_collection,
    }


@router.get("/monitor")
def monitor(
    days: int = Query(default=None, ge=1, le=90, description="Restrict to events within the last N days"),
):
    """
    Fetch active wildfire + storm events and download a Sentinel-2 image
    for each event that has valid coordinates.

    Returns a summary with counts and per-image details.
    """
    # Step 1 — fetch events
    try:
        wildfires = nasa_service.fetch_wildfires(days=days)
        storms    = nasa_service.fetch_storms(days=days)
    except NasaServiceError as exc:
        raise HTTPException(status_code=502, detail=f"NASA EONET error: {exc}")

    all_events = [("wildfire", e) for e in wildfires] + [("storm", e) for e in storms]

    downloaded = []
    failed     = []

    # Step 2 — download an image for each event with valid coordinates
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")

    for event_type, event in all_events:
        coords = event.coordinates
        if not coords or len(coords) < 2:
            logger.debug("Skipping event %s — no coordinates.", event.event_id)
            continue

        geo = event.latest_geometry
        if geo is None:
            logger.debug("Skipping event %s — no geometry.", event.event_id)
            continue

        lat, lon = geo.latitude, geo.longitude
        filename = f"{event_type}_{timestamp}_lat{lat:.4f}_lon{lon:.4f}.png"

        try:
            result = sentinel_service.fetch_image(latitude=lat, longitude=lon)
            saved  = image_service.save(
                array=result.array,
                event_type=event_type,
                latitude=lat,
                longitude=lon,
                filename=filename,
            )
            downloaded.append({
                "event_id":  event.event_id,
                "title":     event.title,
                "type":      event_type,
                "image_url": f"http://127.0.0.1:8000/{saved.image_path}",
                "filename":  saved.filename,
                "latitude":  lat,
                "longitude": lon,
            })
        except (SentinelServiceError, AuthenticationError, EnvironmentError, OSError) as exc:
            logger.warning("Image download failed for %s: %s", event.event_id, exc)
            failed.append({
                "event_id": event.event_id,
                "title":    event.title,
                "error":    str(exc),
            })

    return {
        "success":          True,
        "wildfires":        len(wildfires),
        "storms":           len(storms),
        "total_events":     len(all_events),
        "images_downloaded": len(downloaded),
        "images_failed":    len(failed),
        "downloaded":       downloaded,
        "failed":           failed,
    }
