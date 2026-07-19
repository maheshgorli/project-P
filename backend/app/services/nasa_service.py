"""
NASA EONET event service.

Responsibilities
----------------
- Fetch natural events from the NASA EONET v3 API
- Filter by category (wildfires, storms, etc.)
- Normalise raw API responses into clean, typed dicts
- Handle all network and parsing errors with structured exceptions

All callers import the module-level ``nasa_service`` singleton and call its
methods — they never touch requests or JSON directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

from app.config import settings

logger = logging.getLogger(__name__)

# ── Exceptions ────────────────────────────────────────────────────────────────

class NasaServiceError(Exception):
    """Raised when the EONET API cannot be reached or returns an unexpected response."""


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EventGeometry:
    """A single geometry entry on a NASA EONET event."""
    coordinates: list[float]          # [longitude, latitude] per GeoJSON convention
    date: Optional[str] = None        # ISO-8601 date string, may be absent

    @property
    def longitude(self) -> float:
        return self.coordinates[0]

    @property
    def latitude(self) -> float:
        return self.coordinates[1]


@dataclass(frozen=True)
class NasaEvent:
    """Normalised representation of a single NASA EONET event."""
    event_id:   str
    title:      str
    category:   str                       # human-readable category title
    category_id: str                      # machine-readable category id
    status:     str                       # "open" | "closed"
    geometries: list[EventGeometry] = field(default_factory=list)
    source_url: Optional[str] = None      # link to original source, if present

    @property
    def latest_geometry(self) -> Optional[EventGeometry]:
        """Most recent geometry entry (first in the list per EONET ordering)."""
        return self.geometries[0] if self.geometries else None

    @property
    def coordinates(self) -> Optional[list[float]]:
        """Convenience shortcut → [longitude, latitude] of the latest position."""
        g = self.latest_geometry
        return g.coordinates if g else None

    def to_dict(self) -> dict:
        """Serialisable representation used by API responses."""
        g = self.latest_geometry
        return {
            "event_id":    self.event_id,
            "title":       self.title,
            "category":    self.category,
            "category_id": self.category_id,
            "status":      self.status,
            "coordinates": g.coordinates if g else None,
            "latitude":    g.latitude    if g else None,
            "longitude":   g.longitude   if g else None,
            "date":        g.date        if g else None,
            "source_url":  self.source_url,
        }


# ── Service class ─────────────────────────────────────────────────────────────

class _NasaService:
    """
    Thin wrapper around the NASA EONET v3 API.

    All methods return plain Python objects; callers decide how to serialise them.
    """

    # Known EONET category IDs
    CATEGORY_WILDFIRES   = "wildfires"
    CATEGORY_STORMS      = "severeStorms"
    CATEGORY_VOLCANOES   = "volcanoes"
    CATEGORY_SEA_LAKES   = "seaLakeIce"
    CATEGORY_DUST        = "dustHaze"
    CATEGORY_FLOODS      = "floods"
    CATEGORY_LANDSLIDES  = "landslides"
    CATEGORY_SNOW        = "snow"
    CATEGORY_TEMP_EXTREME = "tempExtremes"
    CATEGORY_WATER_COLOR  = "waterColor"

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch_events(
        self,
        *,
        category_id: Optional[str] = None,
        status: str = "open",
        limit: int = 300,
        days: Optional[int] = None,
    ) -> list[NasaEvent]:
        """
        Fetch events from EONET, optionally filtered by category.

        Args:
            category_id: EONET category string (e.g. "wildfires"). None = all.
            status:       "open" | "closed" | "all"
            limit:        Maximum number of events to return (default 300).
            days:         If set, restrict to events within the last N days.

        Returns:
            List of NasaEvent objects.

        Raises:
            NasaServiceError: on any network or HTTP error.
        """
        raw = self._get_raw_events(status=status, limit=limit, days=days)
        events = [self._parse_event(e) for e in raw]

        if category_id:
            events = [e for e in events if e.category_id == category_id]

        logger.info(
            "EONET fetch — category: %s, status: %s, returned: %d event(s).",
            category_id or "all",
            status,
            len(events),
        )
        return events

    def fetch_wildfires(self, **kwargs) -> list[NasaEvent]:
        """Shortcut for fetch_events(category_id='wildfires')."""
        return self.fetch_events(category_id=self.CATEGORY_WILDFIRES, **kwargs)

    def fetch_storms(self, **kwargs) -> list[NasaEvent]:
        """Shortcut for fetch_events(category_id='severeStorms')."""
        return self.fetch_events(category_id=self.CATEGORY_STORMS, **kwargs)

    def fetch_all_active(self) -> dict[str, list[NasaEvent]]:
        """
        Fetch all open events grouped by category_id.

        Returns:
            Dict mapping category_id → list of NasaEvent.
        """
        events = self.fetch_events(status="open")
        groups: dict[str, list[NasaEvent]] = {}
        for event in events:
            groups.setdefault(event.category_id, []).append(event)
        return groups

    def check_api_status(self) -> dict:
        """
        Ping the EONET endpoint and return connection health info.

        Returns a dict with keys: reachable, status_code, message.
        """
        try:
            resp = requests.get(
                settings.NASA_EONET_URL,
                params={"api_key": settings.nasa_api_key, "limit": 1},
                timeout=8,
            )
            return {
                "reachable":   True,
                "status_code": resp.status_code,
                "message":     "NASA EONET API is reachable.",
            }
        except requests.Timeout:
            return {
                "reachable":   False,
                "status_code": None,
                "message":     "NASA EONET request timed out.",
            }
        except requests.RequestException as exc:
            return {
                "reachable":   False,
                "status_code": None,
                "message":     f"Cannot reach NASA EONET: {exc}",
            }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_raw_events(
        self,
        status: str,
        limit: int,
        days: Optional[int],
    ) -> list[dict]:
        """Make the HTTP request and return the raw events list."""
        params: dict = {
            "api_key": settings.nasa_api_key,
            "status":  status,
            "limit":   limit,
        }
        if days:
            params["days"] = days

        logger.debug("GET %s  params=%s", settings.NASA_EONET_URL, {k: v for k, v in params.items() if k != "api_key"})

        try:
            response = requests.get(settings.NASA_EONET_URL, params=params, timeout=12)
            response.raise_for_status()
        except requests.Timeout:
            raise NasaServiceError(
                f"NASA EONET request timed out (12 s). "
                f"Endpoint: {settings.NASA_EONET_URL}"
            )
        except requests.HTTPError as exc:
            resp = exc.response
            status = str(resp.status_code) if resp is not None else "unknown"
            body = resp.text[:200] if resp is not None else "No response body"
            raise NasaServiceError(
                f"NASA EONET returned HTTP {status}: {body}"
            ) from exc
        except requests.ConnectionError as exc:
            raise NasaServiceError(
                f"Cannot connect to NASA EONET ({settings.NASA_EONET_URL}): {exc}"
            ) from exc
        except requests.RequestException as exc:
            raise NasaServiceError(f"Unexpected error fetching EONET data: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise NasaServiceError(
                f"EONET returned non-JSON response: {response.text[:200]}"
            ) from exc

        if "events" not in body:
            raise NasaServiceError(
                f"EONET response missing 'events' key. Got: {list(body.keys())}"
            )

        return body["events"]

    @staticmethod
    def _parse_event(raw: dict) -> NasaEvent:
        """Convert a single raw EONET event dict into a NasaEvent."""
        categories = raw.get("categories", [])
        # Some events have multiple categories — take the first
        primary = categories[0] if categories else {}

        geometries = [
            EventGeometry(
                coordinates=g.get("coordinates", []),
                date=g.get("date"),
            )
            for g in raw.get("geometry", [])
            if g.get("coordinates")
        ]

        # Pull the first source URL if present
        sources = raw.get("sources", [])
        source_url = sources[0].get("url") if sources else None

        return NasaEvent(
            event_id=raw.get("id", ""),
            title=raw.get("title", "Unnamed event"),
            category=primary.get("title", "Unknown"),
            category_id=primary.get("id", "unknown"),
            status=raw.get("status", "unknown"),
            geometries=geometries,
            source_url=source_url,
        )

    # ── Legacy helpers kept for backward compatibility ────────────────────────

    def get_nasa_key(self) -> str:
        """Return the configured NASA API key."""
        return settings.nasa_api_key


# ── Module-level singleton ─────────────────────────────────────────────────────

nasa_service = _NasaService()

# Keep the original function name importable so existing code doesn't break
def get_nasa_key() -> str:
    return nasa_service.get_nasa_key()
