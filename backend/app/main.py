import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("vauban.log"),
    ],
)
logger = logging.getLogger("vauban")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models.database import engine, SessionLocal, Base
from app.models.airbase import Airbase
from app.api import airbases, observations, sentinel, tiles, analytics, bulk, aircraft


def seed_airbases(db):
    """Load airbase seed data if the table is empty."""
    if db.query(Airbase).count() > 0:
        return

    seed_path = Path(__file__).parent / "data" / "airbases_seed.json"
    with open(seed_path) as f:
        data = json.load(f)

    for entry in data:
        db.add(Airbase(**entry))

    db.commit()
    print(f"Seeded {len(data)} airbases")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_airbases(db)
        from app.api.airbases import restore_zones_from_backup
        restore_zones_from_backup(db)
    finally:
        db.close()

    # Ensure storage directories exist
    Path(settings.image_storage_path).mkdir(parents=True, exist_ok=True)

    yield


app = FastAPI(
    title="Vauban",
    description="IMINT & Military Intelligence Platform - Russian Airbase Monitoring",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(airbases.router)
app.include_router(observations.router)
app.include_router(sentinel.router)
app.include_router(tiles.router)
app.include_router(analytics.router)
app.include_router(bulk.router)
app.include_router(aircraft.router)

# Serve stored images
Path(settings.image_storage_path).mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=settings.image_storage_path), name="images")

# Serve aircraft reference photos
aircraft_img_dir = Path(settings.image_storage_path).parent / "aircraft_images"
aircraft_img_dir.mkdir(parents=True, exist_ok=True)
app.mount("/aircraft", StaticFiles(directory=str(aircraft_img_dir)), name="aircraft")


@app.get("/")
def root():
    return {
        "name": "Vauban",
        "version": "0.1.0",
        "description": "IMINT & Military Intelligence Platform",
    }
