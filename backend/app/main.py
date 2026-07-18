import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# config must be imported first — it calls load_dotenv() exactly once
from app.config import settings
from app.routers.satellite import router as satellite_router
from app.routers.gallery import router as gallery_router

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Geo Satellite Tracking Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
os.makedirs(IMAGES_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

app.include_router(satellite_router)
app.include_router(gallery_router)


@app.on_event("startup")
async def _startup() -> None:
    """Log which environment variables were loaded successfully on startup."""
    settings.log_loaded_vars()


@app.get("/")
def home():
    return {
        "message": "Geo Satellite Tracking Platform API is running",
        "endpoints": {
            "health_check": "/",
            "nasa_all_events_status": "/satellite",
            "wildfires": "/wildfires",
            "storms": "/storms",
            "monitor": "/monitor",
            "gallery": "/gallery",
            "sentinel_auth_test": "/sentinel-test",
            "satellite_image": "/satellite-image?latitude=<float>&longitude=<float>",
        },
    }
