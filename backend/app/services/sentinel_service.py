import os
from dotenv import load_dotenv
from sentinelhub import SHConfig

env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".env"
)

load_dotenv(env_path)

# Copernicus Data Space Ecosystem (CDSE) endpoints.
# Credentials created at dataspace.copernicus.eu ONLY work against these URLs.
# The sentinelhub library defaults to services.sentinel-hub.com, which will
# reject CDSE credentials with (invalid_client).
_CDSE_BASE_URL = "https://sh.dataspace.copernicus.eu"
_CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)


def get_config():
    client_id = os.getenv("SENTINEL_CLIENT_ID", "").strip()
    client_secret = os.getenv("SENTINEL_CLIENT_SECRET", "").strip()

    # Debug: confirm which env vars were loaded (names only, never values)
    loaded = []
    if client_id:
        loaded.append("SENTINEL_CLIENT_ID")
    if client_secret:
        loaded.append("SENTINEL_CLIENT_SECRET")
    print(f"[sentinel_service] Loaded env vars: {loaded}")
    print(f"[sentinel_service] Token URL: {_CDSE_TOKEN_URL}")

    if not client_id:
        raise ValueError("Client ID missing: set SENTINEL_CLIENT_ID in backend/.env")
    if not client_secret:
        raise ValueError("Client Secret missing: set SENTINEL_CLIENT_SECRET in backend/.env")

    config = SHConfig(
        sh_client_id=client_id,
        sh_client_secret=client_secret,
        sh_base_url=_CDSE_BASE_URL,
        sh_token_url=_CDSE_TOKEN_URL,
    )

    return config
