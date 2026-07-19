"""
Pydantic schemas for the /api/* endpoints.

Every response is wrapped in ApiResponse:
    {
        "success": true,
        "message": "Human-readable summary",
        "data": { ... }       # null on error
        "error": null         # populated on failure
    }

Keeping all schemas here makes it easy to generate an OpenAPI spec and
to maintain consistent field names across every endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


# ── Envelope ──────────────────────────────────────────────────────────────────

class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.

    All /api/* endpoints return this shape so the frontend can always
    branch on `success` without inspecting HTTP status codes.
    """
    success: bool
    message: str
    data:    Optional[T]  = None
    error:   Optional[str] = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "OK") -> "ApiResponse":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, error: str, message: str = "Request failed") -> "ApiResponse":
        return cls(success=False, message=message, error=error)


# ── Status / health ───────────────────────────────────────────────────────────

class ServiceStatus(BaseModel):
    name:        str
    reachable:   bool
    status_code: Optional[int] = None
    message:     str


class StatusData(BaseModel):
    api:     str = "Geo Satellite Tracking Platform"
    version: str = "1.0.0"
    services: list[ServiceStatus]


# ── Token ─────────────────────────────────────────────────────────────────────

class TokenData(BaseModel):
    access_token:      str = Field(description="Redacted — first 10 chars only")
    expires_in:        int = Field(description="Total lifetime in seconds")
    token_type:        str
    seconds_remaining: int = Field(description="Seconds until the token should be refreshed")


# ── Image request / response ──────────────────────────────────────────────────

class ImageRequest(BaseModel):
    """Body for POST /api/image."""
    latitude:   float = Field(default=17.3850,  ge=-90,   le=90,   description="Centre latitude")
    longitude:  float = Field(default=78.4867,  ge=-180,  le=180,  description="Centre longitude")
    date_from:  str   = Field(default="2024-01-01",       description="Start date YYYY-MM-DD")
    date_to:    str   = Field(default="2024-06-30",       description="End date YYYY-MM-DD")
    resolution: int   = Field(default=60,       ge=10,    le=1000, description="Metres per pixel")
    bbox_size:  float = Field(default=0.05,     gt=0,     le=5.0,  description="BBox half-extent in degrees")
    event_type: str   = Field(default="satellite",        description="Label: satellite | wildfire | storm")

    @field_validator("date_from", "date_to")
    @classmethod
    def _valid_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Expected YYYY-MM-DD, got: {v!r}")
        return v


class ImageData(BaseModel):
    """Metadata returned for a single stored image."""
    filename:        str
    image_url:       str
    image_path:      str
    disaster_type:   str
    location:        str
    latitude:        Optional[float]
    longitude:       Optional[float]
    date:            str
    captured_at:     str
    file_size_bytes: int
    resolution_meters: Optional[int]  = None
    image_size_pixels: Optional[dict] = None
    date_from:       Optional[str]    = None
    date_to:         Optional[str]    = None
    bbox:            Optional[list[float]] = None
    data_collection: Optional[str]   = None
    prediction:      str = "Pending"
    confidence:      float = 0.0


# ── Gallery ───────────────────────────────────────────────────────────────────

class GalleryData(BaseModel):
    total:  int
    images: list[ImageData]


# ── Disasters ─────────────────────────────────────────────────────────────────

class DisasterEvent(BaseModel):
    event_id:    str
    title:       str
    category:    str
    category_id: str
    status:      str
    coordinates: Optional[list[float]] = None
    latitude:    Optional[float]       = None
    longitude:   Optional[float]       = None
    date:        Optional[str]         = None
    source_url:  Optional[str]         = None


class DisastersData(BaseModel):
    total:      int
    wildfires:  int
    storms:     int
    events:     list[DisasterEvent]


# ── Monitor / history ─────────────────────────────────────────────────────────

class MonitorDownloaded(BaseModel):
    event_id:  str
    title:     str
    type:      str
    image_url: str
    filename:  str
    latitude:  float
    longitude: float


class MonitorFailed(BaseModel):
    event_id: Optional[str] = None
    title:    Optional[str] = None
    error:    str


class MonitorData(BaseModel):
    wildfires:         int
    storms:            int
    total_events:      int
    images_downloaded: int
    images_failed:     int
    downloaded:        list[MonitorDownloaded]
    failed:            list[MonitorFailed]


# ── Delete ────────────────────────────────────────────────────────────────────

class DeleteData(BaseModel):
    filename: str
    deleted:  bool
