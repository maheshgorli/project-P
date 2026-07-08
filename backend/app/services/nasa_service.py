import os
from dotenv import load_dotenv

env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".env"
)

load_dotenv(env_path)

def get_nasa_key():
    return os.getenv("NASA_API_KEY", "NO_KEY_FOUND")