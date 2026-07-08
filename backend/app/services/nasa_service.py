import os
from dotenv import load_dotenv

env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".env"
)

load_dotenv(env_path)

# TODO: wire this into satellite.py requests once NASA API key auth is needed (see Phase 4).
def get_nasa_key():
    """
    Returns the NASA API key from the environment.

    NASA_API_KEY is optional for EONET's public endpoints — DEMO_KEY works fine
    for development and low-traffic use. A real key is required for production to
    avoid rate-limit errors (DEMO_KEY is capped at 30 req/hour, 50 req/day).

    Get a free key at: https://api.nasa.gov/
    """
    return os.getenv("NASA_API_KEY", "DEMO_KEY")