"""
Sentinel Hub service — authentication + imagery.

Responsibilities
----------------
- Build and cache a valid SHConfig (delegating OAuth to token_service)
- Fetch Sentinel-2 true-colour imagery for any coordinate/date-range/resolution
- Return raw numpy arrays — file I/O is handled by image_service

Public API
----------
    from app.services.sentinel_service import sentinel_service, AuthenticationError, SentinelServiceError

    # Auth check
    token = sentinel_service.get_token()

    # Fetch an image array
    result = sentinel_service.fetch_image(
        latitude=17.385,
        longitude=78.487,
        date_from="2024-01-01",
        date_to="2024-06-30",
        resolution=60,
        bbox_size=0.05,
    )
    # result.array  → numpy uint8 (H, W, 3)
    # result.meta   → SentinelImageMeta
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sentinelhub.geometry import BBox
from sentinelhub.constants import CRS, MimeType, MosaickingOrder
from sentinelhub.data_collections import DataCollection
from sentinelhub.api.process import SentinelHubRequest
from sentinelhub.config import SHConfig
from sentinelhub.geo_utils import bbox_to_dimensions

from app.config import settings
from app.services.token_service import token_service, TokenResponse, AuthenticationError

logger = logging.getLogger(__name__)

# Re-export for callers that need to catch auth errors
__all__ = ["sentinel_service", "AuthenticationError", "SentinelServiceError"]

# ── Exceptions ────────────────────────────────────────────────────────────────

class SentinelServiceError(Exception):
    """Raised when a Sentinel Hub imagery request fails."""


# ── Constants ─────────────────────────────────────────────────────────────────

_CDSE_BASE_URL  = settings.SENTINEL_BASE_URL
_CDSE_TOKEN_URL = settings.SENTINEL_TOKEN_URL

# Re-define the collection with the correct CDSE service_url.
# DataCollection.SENTINEL2_L1C hard-codes services.sentinel-hub.com, which
# rejects CDSE credentials.
_SENTINEL2_L1C_CDSE = DataCollection.SENTINEL2_L1C.define_from(
    "SENTINEL2_L1C_CDSE",
    service_url=_CDSE_BASE_URL,
)

# True-colour evalscript — Sentinel-2 B04/B03/B02 RGB with brightness boost
_EVALSCRIPT_TRUE_COLOR = """
//VERSION=3
function setup() {
    return {
        input:  [{ bands: ["B02", "B03", "B04"] }],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    return [3.5 * sample.B04, 3.5 * sample.B03, 3.5 * sample.B02];
}
"""

# Defaults used when callers don't supply their own
DEFAULT_LATITUDE  = 17.3850   # Hyderabad, India
DEFAULT_LONGITUDE = 78.4867
DEFAULT_DATE_FROM = "2024-01-01"
DEFAULT_DATE_TO   = "2024-06-30"
DEFAULT_RESOLUTION = 60        # metres per pixel
DEFAULT_BBOX_SIZE  = 0.05      # degrees (±0.05° ≈ ±5.5 km)


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SentinelImageMeta:
    """Metadata accompanying a successfully fetched Sentinel-2 image."""
    latitude:          float
    longitude:         float
    date_from:         str
    date_to:           str
    bbox:              list[float]   # [lon_min, lat_min, lon_max, lat_max]
    resolution_meters: int
    image_size_pixels: dict          # {"width": W, "height": H}
    data_collection:   str = "SENTINEL2_L1C"
    mosaicking_order:  str = "leastCC"


@dataclass
class SentinelImageResult:
    """Return type of sentinel_service.fetch_image()."""
    array: np.ndarray      # uint8, shape (H, W, 3)
    meta:  SentinelImageMeta


# ── Service class ─────────────────────────────────────────────────────────────

class _SentinelService:
    """
    Facade for all Sentinel Hub interactions.

    Methods are stateless except for the SHConfig which is rebuilt when
    the cached OAuth token is refreshed.
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def get_token(self) -> TokenResponse:
        """
        Return a valid CDSE OAuth token (cached, auto-refreshed).

        Raises:
            AuthenticationError: if the token cannot be obtained.
            EnvironmentError:    if credentials are not set.
        """
        return token_service.get_token()

    def get_config(self) -> SHConfig:
        """
        Return an SHConfig pre-loaded with CDSE endpoints.

        Validates credentials eagerly by fetching a token before returning,
        so misconfiguration surfaces immediately.

        Raises:
            AuthenticationError: if the token cannot be obtained.
            EnvironmentError:    if credentials are not set.
        """
        token = token_service.get_token()
        logger.debug(
            "SHConfig built — token seconds_remaining: %d",
            round(token.seconds_remaining),
        )
        return SHConfig(
            sh_client_id=settings.sentinel_client_id,
            sh_client_secret=settings.sentinel_client_secret,
            sh_base_url=_CDSE_BASE_URL,
            sh_token_url=_CDSE_TOKEN_URL,
        )

    def fetch_image(
        self,
        latitude:         float  = DEFAULT_LATITUDE,
        longitude:        float  = DEFAULT_LONGITUDE,
        date_from:        str    = DEFAULT_DATE_FROM,
        date_to:          str    = DEFAULT_DATE_TO,
        resolution:       int    = DEFAULT_RESOLUTION,
        bbox_size:        float  = DEFAULT_BBOX_SIZE,
        mosaicking_order: str    = "leastCC",
    ) -> SentinelImageResult:
        """
        Fetch a true-colour Sentinel-2 image for the given parameters.

        Args:
            latitude:         Centre latitude in decimal degrees.
            longitude:        Centre longitude in decimal degrees.
            date_from:        Start of the acquisition window, ISO-8601 (YYYY-MM-DD).
            date_to:          End   of the acquisition window, ISO-8601 (YYYY-MM-DD).
            resolution:       Metres per pixel. Lower = sharper, larger file.
                              Recommended: 10 (high), 30 (medium), 60 (fast preview).
            bbox_size:        Half-extent of the bounding box in degrees.
                              0.05° ≈ 5.5 km, 0.1° ≈ 11 km from centre.
            mosaicking_order: How Sentinel Hub picks tiles when multiple overlap.
                              "leastCC" (least cloud cover) is recommended.

        Returns:
            SentinelImageResult with .array (uint8 numpy) and .meta.

        Raises:
            SentinelServiceError: if the request fails for any reason.
            AuthenticationError:  if credentials are invalid.
            EnvironmentError:     if credentials are not set.
        """
        self._validate_date_range(date_from, date_to)
        self._validate_coordinates(latitude, longitude)
        self._validate_resolution(resolution)

        bbox_coords = (
            longitude - bbox_size,
            latitude  - bbox_size,
            longitude + bbox_size,
            latitude  + bbox_size,
        )
        bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
        size = bbox_to_dimensions(bbox, resolution=resolution)

        logger.info(
            "Fetching Sentinel-2 image — lat=%.4f lon=%.4f  "
            "%s → %s  res=%dm  bbox±%.3f°  size=%dx%d",
            latitude, longitude, date_from, date_to,
            resolution, bbox_size, size[0], size[1],
        )

        config = self.get_config()

        try:
            request = SentinelHubRequest(
                evalscript=_EVALSCRIPT_TRUE_COLOR,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=_SENTINEL2_L1C_CDSE,
                        time_interval=(date_from, date_to),
                        mosaicking_order=MosaickingOrder(mosaicking_order),
                    )
                ],
                responses=[
                    SentinelHubRequest.output_response("default", MimeType.PNG)
                ],
                bbox=bbox,
                size=size,
                config=config,
            )
            images = request.get_data()
        except AuthenticationError:
            raise   # let auth errors propagate as-is
        except Exception as exc:
            raise SentinelServiceError(
                f"Sentinel Hub request failed: {exc}"
            ) from exc

        if not images or images[0] is None:
            raise SentinelServiceError(
                "Sentinel Hub returned no image data. "
                "The area or date range may have no available imagery."
            )

        array = images[0]
        if array.dtype != np.uint8:
            array = (np.clip(array, 0, 1) * 255).astype(np.uint8)

        meta = SentinelImageMeta(
            latitude=latitude,
            longitude=longitude,
            date_from=date_from,
            date_to=date_to,
            bbox=list(bbox_coords),
            resolution_meters=resolution,
            image_size_pixels={"width": size[0], "height": size[1]},
            mosaicking_order=mosaicking_order,
        )

        logger.info(
            "Image received — shape: %s  dtype: %s",
            array.shape, array.dtype,
        )
        return SentinelImageResult(array=array, meta=meta)

    # ── Validation helpers ────────────────────────────────────────────────────

    @staticmethod
    def _validate_date_range(date_from: str, date_to: str) -> None:
        from datetime import date as _date
        try:
            d_from = _date.fromisoformat(date_from)
            d_to   = _date.fromisoformat(date_to)
        except ValueError as exc:
            raise ValueError(
                f"Invalid date format — expected YYYY-MM-DD, got: '{exc}'"
            ) from exc
        if d_from > d_to:
            raise ValueError(
                f"date_from ({date_from}) must be before date_to ({date_to})."
            )

    @staticmethod
    def _validate_coordinates(latitude: float, longitude: float) -> None:
        if not (-90 <= latitude <= 90):
            raise ValueError(f"latitude must be between -90 and 90, got {latitude}.")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"longitude must be between -180 and 180, got {longitude}.")

    @staticmethod
    def _validate_resolution(resolution: int) -> None:
        if resolution < 10 or resolution > 1000:
            raise ValueError(
                f"resolution must be between 10 and 1000 metres, got {resolution}."
            )


# ── Module-level singleton ─────────────────────────────────────────────────────

sentinel_service = _SentinelService()

# ── Legacy aliases — keep existing import paths working ───────────────────────

def get_token() -> TokenResponse:
    return sentinel_service.get_token()

def get_config() -> SHConfig:
    return sentinel_service.get_config()
