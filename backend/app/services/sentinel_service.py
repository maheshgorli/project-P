"""
Sentinel Hub authentication service.

Builds a SHConfig pointed at the Copernicus Data Space Ecosystem (CDSE).
Credentials are read from the central settings object (which loads .env once
at startup via app.config).
"""

import logging
from sentinelhub import SHConfig
from app.config import settings

logger = logging.getLogger(__name__)

# Re-export so image_service can import the URL without depending on config directly
_CDSE_BASE_URL  = settings.SENTINEL_BASE_URL
_CDSE_TOKEN_URL = settings.SENTINEL_TOKEN_URL


def get_config() -> SHConfig:
    """
    Return a SHConfig configured for CDSE.

    Raises:
        EnvironmentError: if SENTINEL_CLIENT_ID or SENTINEL_CLIENT_SECRET are missing.
    """
    # _require() inside settings raises EnvironmentError with a clear message
    client_id     = settings.sentinel_client_id
    client_secret = settings.sentinel_client_secret

    logger.debug(
        "Building SHConfig — client_id prefix: %s..., token_url: %s",
        client_id[:8],
        _CDSE_TOKEN_URL,
    )

    return SHConfig(
        sh_client_id=client_id,
        sh_client_secret=client_secret,
        sh_base_url=_CDSE_BASE_URL,
        sh_token_url=_CDSE_TOKEN_URL,
    )
