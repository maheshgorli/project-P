import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# config must be imported first — it calls load_dotenv() exactly once
from app.config import settings
from app.routers.api import router as api_router
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
app = FastAPI(
    title="Geo Satellite Tracking Platform",
    description=(
        "REST API for satellite imagery, NASA EONET disaster events, "
        "and Sentinel Hub integration.\n\n"
        "All `/api/*` endpoints return a uniform JSON envelope:\n"
        "```json\n"
        '{"success": true, "message": "...", "data": {}, "error": null}\n'
        "```"
    ),
    version="1.0.0",
)

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

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(api_router)          # /api/*  — primary REST API
app.include_router(satellite_router)    # legacy routes (kept for backward compat)
app.include_router(gallery_router)      # legacy /gallery


@app.on_event("startup")
async def _startup() -> None:
    settings.log_loaded_vars()


@app.get("/", tags=["Root"])
def home():
    return {
        "message": "Geo Satellite Tracking Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "api": {
            "status":       "GET  /api/status",
            "token":        "GET  /api/token",
            "latest_image": "GET  /api/latest-image",
            "capture_image":"POST /api/image",
            "gallery":      "GET  /api/gallery",
            "disasters":    "GET  /api/disasters",
            "history":      "GET  /api/history",
            "delete_image": "DELETE /api/image/{filename}",
        },
        "legacy": {
            "wildfires":    "/wildfires",
            "storms":       "/storms",
            "monitor":      "/monitor",
            "gallery":      "/gallery",
            "sentinel_test":"/sentinel-test",
            "auth_token":   "/auth/token",
        },
    }
