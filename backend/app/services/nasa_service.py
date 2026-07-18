"""
NASA API key accessor.

NASA_API_KEY is optional — EONET's public endpoints accept the shared DEMO_KEY
for development and low-traffic usage (capped at 30 req/hr, 50 req/day).
Set a real key in backend/.env for production use.  Get one free at:
https://api.nasa.gov/
"""

from app.config import settings


def get_nasa_key() -> str:
    """Return the NASA API key (falls back to 'DEMO_KEY' if unset)."""
    return settings.nasa_api_key
