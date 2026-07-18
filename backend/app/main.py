import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers.satellite import router as satellite_router
from app.routers.gallery import router as gallery_router

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
