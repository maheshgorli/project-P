"""
Central configuration module.

Loads the .env file exactly once at startup and exposes validated settings.
All other modules import from here — no scattered load_dotenv() calls elsewhere.

Resolution order for the .env path (first found wins):
  1. DOTENV_PATH environment variable  — lets CI/Docker override it
  2. backend/.env relative to this file's location  — standard dev layout
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Locate and load .env ────────────────────────────────────────────────────

# This file lives at  backend/app/config.py
# backend/.env is two levels up: backend/app/ → backend/
_DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
_ENV_PATH = Path(os.environ.get("DOTENV_PATH", _DEFAULT_ENV_PATH))

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH, override=False)   # don't clobber vars already set in the shell
    logger.info("Loaded .env from %s", _ENV_PATH)
else:
    logger.warning(
        ".env file not found at %s — relying on environment variables only.",
        _ENV_PATH,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _require(name: str) -> str:
    """Return the value of an env var, or raise a clear error if it is missing."""
    value = os.getenv(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set.\n"
            f"  → Add it to {_ENV_PATH} or export it in your shell.\n"
            f"  → See backend/.env.example for the full list of required variables."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    """Return the value of an optional env var, or the default."""
    return os.getenv(name, default).strip() or default


# ── Settings ─────────────────────────────────────────────────────────────────

class _Settings:
    """
    Thin settings container.  Values are read lazily on first access so that
    a missing variable raises an error at the call site, not at import time.
    This lets the app start (and serve /docs, /wildfires, etc.) even when
    Sentinel Hub credentials are not yet configured.
    """

    # --- Sentinel Hub (required when calling Sentinel endpoints) ---

    @property
    def sentinel_client_id(self) -> str:
        return _require("SENTINEL_CLIENT_ID")

    @property
    def sentinel_client_secret(self) -> str:
        return _require("SENTINEL_CLIENT_SECRET")

    # --- NASA EONET (optional — DEMO_KEY is the public fallback) ---

    @property
    def nasa_api_key(self) -> str:
        key = _optional("NASA_API_KEY")
        if not key or key == "your_nasa_api_key_here":
            logger.debug(
                "NASA_API_KEY not set — using DEMO_KEY "
                "(rate-limited to 30 req/hr; set a real key for production)."
            )
            return "DEMO_KEY"
        return key

    # --- Sentinel Hub CDSE endpoints (not secrets, but centralised here) ---

    SENTINEL_BASE_URL: str = "https://sh.dataspace.copernicus.eu"
    SENTINEL_TOKEN_URL: str = (
        "https://identity.dataspace.copernicus.eu"
        "/auth/realms/CDSE/protocol/openid-connect/token"
    )

    # --- NASA EONET ---

    NASA_EONET_URL: str = "https://eonet.gsfc.nasa.gov/api/v3/events"

    def log_loaded_vars(self) -> None:
        """Log which env-var names are present (never logs values)."""
        names = ["SENTINEL_CLIENT_ID", "SENTINEL_CLIENT_SECRET", "NASA_API_KEY"]
        loaded   = [n for n in names if os.getenv(n, "").strip()]
        missing  = [n for n in names if not os.getenv(n, "").strip()]
        if loaded:
            logger.info("Env vars loaded: %s", loaded)
        if missing:
            logger.warning("Env vars not set: %s", missing)


settings = _Settings()
