from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers.satellite import router as satellite_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(satellite_router)

@app.get("/")
def home():
    return {"message": "working"}