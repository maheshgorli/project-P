import os
from dotenv import load_dotenv
from sentinelhub import SHConfig

env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".env"
)

load_dotenv(env_path)


def get_config():
    config = SHConfig()
    config.sh_client_id = os.getenv("SENTINEL_CLIENT_ID")
    config.sh_client_secret = os.getenv("SENTINEL_CLIENT_SECRET")

    if not config.sh_client_id:
        raise ValueError("Client ID missing: set SENTINEL_CLIENT_ID in backend/.env")
    if not config.sh_client_secret:
        raise ValueError("Client Secret missing: set SENTINEL_CLIENT_SECRET in backend/.env")

    return config
