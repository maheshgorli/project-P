import os
from dotenv import load_dotenv

env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".env"
)

load_dotenv(env_path)

# TODO: wire this into satellite.py requests once NASA API key auth is needed (see Phase 4).
def get_nasa_key():
    return os.getenv("NASA_API_KEY", "NO_KEY_FOUND")