from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db
from app.models.airbase import Airbase, CaptureZone

router = APIRouter(prefix="/api/airbases", tags=["airbases"])


class CaptureZoneOut(BaseModel):
    id: int
    label: str | None
    latitude: float
    longitude: float
    zoom: int
    grid_size: int
    model_config = {"from_attributes": True}


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
    capture_zones: list[CaptureZoneOut] = []
    model_config = {"from_attributes": True}


class CoordsUpdate(BaseModel):
    latitude: float
    longitude: float


class ZoneCreate(BaseModel):
    label: str | None = None
    latitude: float
    longitude: float
    zoom: int = 17
    grid_size: int = 6


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


@router.post("/{airbase_id}/zones", response_model=CaptureZoneOut)
def add_zone(airbase_id: int, zone: ZoneCreate, db: Session = Depends(get_db)):
    """Add a capture zone to an airbase."""
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")
    cz = CaptureZone(
        airbase_id=airbase_id,
        label=zone.label,
        latitude=zone.latitude,
        longitude=zone.longitude,
        zoom=zone.zoom,
        grid_size=zone.grid_size,
    )
    db.add(cz)
    db.commit()
    db.refresh(cz)
    return cz


@router.delete("/{airbase_id}/zones/{zone_id}")
def delete_zone(airbase_id: int, zone_id: int, db: Session = Depends(get_db)):
    """Remove a capture zone."""
    cz = db.query(CaptureZone).filter(CaptureZone.id == zone_id, CaptureZone.airbase_id == airbase_id).first()
    if not cz:
        raise HTTPException(status_code=404, detail="Zone not found")
    db.delete(cz)
    db.commit()
    return {"status": "deleted"}
