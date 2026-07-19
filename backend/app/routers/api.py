"""
REST API router — all endpoints live under the /api prefix.

Every endpoint returns ApiResponse:
    { "success": bool, "message": str, "data": <model> | null, "error": str | null }

Endpoints
---------
GET    /api/status          — platform + dependency health check
GET    /api/token           — current OAuth token info (redacted)
GET    /api/latest-image    — metadata for the most recently saved image
POST   /api/image           — fetch + save a Sentinel-2 image (body: ImageRequest)
GET    /api/gallery         — all stored images, newest first
GET    /api/disasters       — active NASA EONET events (wildfires + storms)
GET    /api/history         — alias for gallery, future-ready for richer filtering
DELETE /api/image/{id}      — delete a stored image by filename
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Path, Query

from app.schemas import (
    ApiResponse,
    DeleteData,
    DisasterEvent,
    DisastersData,
    GalleryData,
    ImageData,
    ImageRequest,
    MonitorData,
    MonitorDownloaded,
    MonitorFailed,
    ServiceStatus,
    StatusData,
    TokenData,
)
from app.services.image_service import image_service
from app.services.nasa_service import nasa_service, NasaServiceError
from app.services.sentinel_service import (
    sentinel_service,
    SentinelServiceError,
    AuthenticationError,
)
from app.services.token_service import token_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["API"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _saved_to_image_data(saved, extra: dict | None = None) -> ImageData:
    """Convert a SavedImage to an ImageData schema, optionally merging extra fields."""
    d = saved.to_dict()
    merged = {**d, **(extra or {})}
    # Build kwargs with defaults matching ImageData field types so required
    # str/int fields never receive None (which Pyright rejects).
    kwargs: dict = {}
    for k, field_info in ImageData.model_fields.items():
        value = merged.get(k)
        if value is not None:
            kwargs[k] = value
        elif field_info.default is not None:
            # Pydantic field has its own default — omit so it kicks in
            pass
        else:
            kwargs[k] = value
    return ImageData(**kwargs)


# ── GET /api/status ────────────────────────────────────────────────────────────

@router.get(
    "/status",
    response_model=ApiResponse[StatusData],
    summary="Platform health check",
    description="Reports reachability of NASA EONET and Sentinel Hub OAuth.",
)
def get_status() -> ApiResponse[StatusData]:
    services: list[ServiceStatus] = []

    # NASA EONET
    nasa_status = nasa_service.check_api_status()
    services.append(ServiceStatus(
        name="NASA EONET",
        reachable=nasa_status["reachable"],
        status_code=nasa_status.get("status_code"),
        message=nasa_status["message"],
    ))

    # Sentinel Hub OAuth
    try:
        token = token_service.get_token()
        services.append(ServiceStatus(
            name="Sentinel Hub (CDSE)",
            reachable=True,
            status_code=200,
            message=(
                f"Authenticated — token valid for "
                f"{round(token.seconds_remaining)} s."
            ),
        ))
        sentinel_ok = True
    except (AuthenticationError, EnvironmentError) as exc:
        services.append(ServiceStatus(
            name="Sentinel Hub (CDSE)",
            reachable=False,
            status_code=None,
            message=str(exc),
        ))
        sentinel_ok = False

    all_ok = nasa_status["reachable"] and sentinel_ok
    return ApiResponse.ok(
        data=StatusData(services=services),
        message="All services operational." if all_ok else "One or more services unavailable.",
    )


# ── GET /api/token ─────────────────────────────────────────────────────────────

@router.get(
    "/token",
    response_model=ApiResponse[TokenData],
    summary="OAuth token info",
    description=(
        "Returns the current cached CDSE OAuth token metadata. "
        "The access_token value is redacted for security."
    ),
)
def get_token() -> ApiResponse[TokenData]:
    try:
        token = token_service.get_token()
    except EnvironmentError as exc:
        return ApiResponse.fail(
            error=str(exc),
            message="Sentinel Hub credentials are not configured.",
        )
    except AuthenticationError as exc:
        return ApiResponse.fail(
            error=str(exc),
            message="OAuth authentication failed.",
        )

    summary = token.redacted_summary()
    return ApiResponse.ok(
        data=TokenData(
            access_token=summary["access_token"],
            expires_in=summary["expires_in"],
            token_type=summary["token_type"],
            seconds_remaining=summary["seconds_remaining"],
        ),
        message=f"Token valid — {summary['seconds_remaining']} seconds remaining.",
    )


# ── GET /api/latest-image ──────────────────────────────────────────────────────

@router.get(
    "/latest-image",
    response_model=ApiResponse[ImageData],
    summary="Most recently saved satellite image",
    description="Returns metadata for the newest image in backend/images/.",
)
def get_latest_image() -> ApiResponse[ImageData]:
    images = image_service.list_images()
    if not images:
        return ApiResponse.fail(
            error="No images found.",
            message="No satellite images have been saved yet. "
                    "Call POST /api/image or GET /api/disasters to download images.",
        )
    latest = images[0]
    return ApiResponse.ok(
        data=_saved_to_image_data(latest),
        message=f"Latest image: {latest.filename}",
    )


# ── POST /api/image ────────────────────────────────────────────────────────────

@router.post(
    "/image",
    response_model=ApiResponse[ImageData],
    summary="Fetch and save a Sentinel-2 image",
    description=(
        "Downloads a true-colour Sentinel-2 image for the given coordinates "
        "and date range, then saves it to disk."
    ),
)
def post_image(body: ImageRequest) -> ApiResponse[ImageData]:
    logger.info(
        "POST /api/image — lat=%.4f lon=%.4f  %s→%s  res=%dm",
        body.latitude, body.longitude,
        body.date_from, body.date_to, body.resolution,
    )

    # Validate date ordering
    if body.date_from >= body.date_to:
        return ApiResponse.fail(
            error=f"date_from ({body.date_from}) must be before date_to ({body.date_to}).",
            message="Invalid date range.",
        )

    try:
        result = sentinel_service.fetch_image(
            latitude=body.latitude,
            longitude=body.longitude,
            date_from=body.date_from,
            date_to=body.date_to,
            resolution=body.resolution,
            bbox_size=body.bbox_size,
        )
        saved = image_service.save(
            array=result.array,
            event_type=body.event_type,
            latitude=body.latitude,
            longitude=body.longitude,
        )
    except ValueError as exc:
        return ApiResponse.fail(error=str(exc), message="Invalid request parameters.")
    except AuthenticationError as exc:
        return ApiResponse.fail(error=str(exc), message="Sentinel Hub authentication failed.")
    except SentinelServiceError as exc:
        return ApiResponse.fail(error=str(exc), message="Sentinel Hub imagery request failed.")
    except OSError as exc:
        return ApiResponse.fail(error=str(exc), message="Failed to save image to disk.")

    extra = {
        "resolution_meters": result.meta.resolution_meters,
        "image_size_pixels": result.meta.image_size_pixels,
        "date_from":         body.date_from,
        "date_to":           body.date_to,
        "bbox":              result.meta.bbox,
        "data_collection":   result.meta.data_collection,
    }
    return ApiResponse.ok(
        data=_saved_to_image_data(saved, extra),
        message=f"Image saved — {saved.filename} ({saved.file_size_bytes:,} bytes).",
    )


# ── GET /api/gallery ───────────────────────────────────────────────────────────

@router.get(
    "/gallery",
    response_model=ApiResponse[GalleryData],
    summary="All stored satellite images",
    description="Returns metadata for every image in backend/images/, newest first.",
)
def get_gallery() -> ApiResponse[GalleryData]:
    images = image_service.list_images()
    image_data = [_saved_to_image_data(img) for img in images]
    return ApiResponse.ok(
        data=GalleryData(total=len(image_data), images=image_data),
        message=f"{len(image_data)} image(s) found.",
    )


# ── GET /api/disasters ─────────────────────────────────────────────────────────

@router.get(
    "/disasters",
    response_model=ApiResponse[DisastersData],
    summary="Active NASA EONET disaster events",
    description=(
        "Returns currently active wildfire and severe-storm events from NASA EONET. "
        "Use the `days` parameter to restrict to events within the last N days."
    ),
)
def get_disasters(
    days: int = Query(
        default=None, ge=1, le=365,
        description="Restrict to events within the last N days (optional).",
    ),
    category: str = Query(
        default=None,
        description="Filter by EONET category id, e.g. 'wildfires', 'severeStorms'. "
                    "Omit to return all active disaster types.",
    ),
) -> ApiResponse[DisastersData]:
    try:
        if category:
            events = nasa_service.fetch_events(category_id=category, days=days)
        else:
            wildfires = nasa_service.fetch_wildfires(days=days)
            storms    = nasa_service.fetch_storms(days=days)
            events    = wildfires + storms
    except NasaServiceError as exc:
        logger.error("GET /api/disasters failed: %s", exc)
        return ApiResponse.fail(
            error=str(exc),
            message="Failed to fetch events from NASA EONET.",
        )

    wf_count = sum(1 for e in events if e.category_id == "wildfires")
    st_count = sum(1 for e in events if e.category_id == "severeStorms")

    disaster_list: list[DisasterEvent] = []
    for e in events:
        ed = e.to_dict()
        disaster_list.append(DisasterEvent(
            event_id=ed.get("event_id", ""),
            title=ed.get("title", ""),
            category=ed.get("category", ""),
            category_id=ed.get("category_id", ""),
            status=ed.get("status", ""),
            coordinates=ed.get("coordinates"),
            latitude=ed.get("latitude"),
            longitude=ed.get("longitude"),
            date=ed.get("date"),
            source_url=ed.get("source_url"),
        ))

    return ApiResponse.ok(
        data=DisastersData(
            total=len(disaster_list),
            wildfires=wf_count,
            storms=st_count,
            events=disaster_list,
        ),
        message=f"{len(disaster_list)} active event(s) — "
                f"{wf_count} wildfire(s), {st_count} storm(s).",
    )


# ── GET /api/history ───────────────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=ApiResponse[GalleryData],
    summary="Image download history",
    description=(
        "Returns the full history of downloaded satellite images, newest first. "
        "Supports optional filtering by disaster_type."
    ),
)
def get_history(
    disaster_type: str = Query(
        default=None,
        description="Filter by type label, e.g. 'Wildfire', 'Severe Storm', 'Satellite Capture'.",
    ),
    limit: int = Query(
        default=100, ge=1, le=1000,
        description="Maximum number of images to return.",
    ),
) -> ApiResponse[GalleryData]:
    images = image_service.list_images()

    if disaster_type:
        images = [
            img for img in images
            if img.disaster_type.lower() == disaster_type.lower()
        ]

    images = images[:limit]
    image_data = [_saved_to_image_data(img) for img in images]

    filter_note = f" (filtered by type: {disaster_type!r})" if disaster_type else ""
    return ApiResponse.ok(
        data=GalleryData(total=len(image_data), images=image_data),
        message=f"{len(image_data)} image(s) in history{filter_note}.",
    )


# ── DELETE /api/image/{id} ─────────────────────────────────────────────────────

@router.delete(
    "/image/{image_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete a stored image",
    description=(
        "Permanently deletes a stored image by its filename. "
        "The `id` path parameter is the full filename "
        "(e.g. `wildfire_2026-07-19_13-00_lat17.3850_lon78.4870.png`)."
    ),
)
def delete_image(
    image_id: str = Path(
        description="The filename of the image to delete (including .png extension).",
    ),
) -> ApiResponse[DeleteData]:
    try:
        deleted = image_service.delete(image_id)
    except ValueError as exc:
        return ApiResponse.fail(
            error=str(exc),
            message="Invalid image identifier.",
        )
    except OSError as exc:
        return ApiResponse.fail(
            error=str(exc),
            message=f"Failed to delete {image_id}.",
        )

    if not deleted:
        return ApiResponse.fail(
            error=f"File not found: {image_id}",
            message=f"Image '{image_id}' does not exist.",
        )

    return ApiResponse.ok(
        data=DeleteData(filename=image_id, deleted=True),
        message=f"Image '{image_id}' deleted successfully.",
    )
