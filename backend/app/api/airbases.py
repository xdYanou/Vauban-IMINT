from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db
from app.models.airbase import Airbase

router = APIRouter(prefix="/api/airbases", tags=["airbases"])


class AirbaseOut(BaseModel):
    id: int
    name: str
    icao_code: str | None
    latitude: float
    longitude: float
    country: str
    region: str | None
    military_district: str | None
    known_units: str | None
    capture_radius_km: float | None
    capture_zoom: int | None

    model_config = {"from_attributes": True}


class CoordsUpdate(BaseModel):
    latitude: float
    longitude: float


class CaptureSettingsUpdate(BaseModel):
    capture_radius_km: float | None = None
    capture_zoom: int | None = None
    latitude: float | None = None
    longitude: float | None = None


@router.get("/", response_model=list[AirbaseOut])
def list_airbases(db: Session = Depends(get_db)):
    return db.query(Airbase).all()


@router.get("/{airbase_id}", response_model=AirbaseOut)
def get_airbase(airbase_id: int, db: Session = Depends(get_db)):
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")
    return airbase


@router.patch("/{airbase_id}/coords", response_model=AirbaseOut)
def update_coords(airbase_id: int, coords: CoordsUpdate, db: Session = Depends(get_db)):
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")
    airbase.latitude = coords.latitude
    airbase.longitude = coords.longitude
    db.commit()
    db.refresh(airbase)
    return airbase


@router.patch("/{airbase_id}/settings", response_model=AirbaseOut)
def update_capture_settings(airbase_id: int, s: CaptureSettingsUpdate, db: Session = Depends(get_db)):
    """Update capture settings — radius, zoom, coordinates."""
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")
    if s.capture_radius_km is not None:
        airbase.capture_radius_km = s.capture_radius_km
    if s.capture_zoom is not None:
        airbase.capture_zoom = s.capture_zoom
    if s.latitude is not None:
        airbase.latitude = s.latitude
    if s.longitude is not None:
        airbase.longitude = s.longitude
    db.commit()
    db.refresh(airbase)
    return airbase
