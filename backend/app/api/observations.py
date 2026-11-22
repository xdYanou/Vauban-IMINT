from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path

from app.models.database import get_db
from app.models.airbase import Airbase, Observation, Detection
from app.services.detection import detection_service
from app.config import settings

router = APIRouter(prefix="/api/observations", tags=["observations"])


class DetectionOut(BaseModel):
    id: int
    aircraft_type: str
    confidence: float
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float

    model_config = {"from_attributes": True}


class ObservationOut(BaseModel):
    id: int
    airbase_id: int
    observation_date: datetime
    image_path: str
    source: str
    cloud_cover_pct: float | None
    detections: list[DetectionOut] = []

    model_config = {"from_attributes": True}


class ObservationSummary(BaseModel):
    id: int
    airbase_id: int
    observation_date: datetime
    source: str
    cloud_cover_pct: float | None
    aircraft_count: int
    aircraft_types: dict[str, int]

    model_config = {"from_attributes": True}


@router.get("/airbase/{airbase_id}", response_model=list[ObservationSummary])
def list_observations(airbase_id: int, db: Session = Depends(get_db)):
    observations = (
        db.query(Observation)
        .filter(Observation.airbase_id == airbase_id)
        .order_by(Observation.observation_date.desc())
        .all()
    )

    summaries = []
    for obs in observations:
        type_counts: dict[str, int] = {}
        for det in obs.detections:
            type_counts[det.aircraft_type] = type_counts.get(det.aircraft_type, 0) + 1

        summaries.append(
            ObservationSummary(
                id=obs.id,
                airbase_id=obs.airbase_id,
                observation_date=obs.observation_date,
                source=obs.source,
                cloud_cover_pct=obs.cloud_cover_pct,
                aircraft_count=len(obs.detections),
                aircraft_types=type_counts,
            )
        )

    return summaries


@router.get("/{observation_id}", response_model=ObservationOut)
def get_observation(observation_id: int, db: Session = Depends(get_db)):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs


@router.delete("/capture/{airbase_id}/{capture_date}")
def delete_capture(airbase_id: int, capture_date: str, db: Session = Depends(get_db)):
    """Delete all observations in a capture session (within 60s of given timestamp)."""
    from datetime import timedelta

    try:
        target = datetime.fromisoformat(capture_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    observations = (
        db.query(Observation)
        .filter(
            Observation.airbase_id == airbase_id,
            Observation.observation_date >= target - timedelta(seconds=60),
            Observation.observation_date <= target + timedelta(seconds=60),
        )
        .all()
    )

    if not observations:
        raise HTTPException(status_code=404, detail="No observations found")

    for obs in observations:
        img_path = Path(obs.image_path)
        if img_path.exists():
            img_path.unlink(missing_ok=True)
        db.query(Detection).filter(Detection.observation_id == obs.id).delete()
        db.delete(obs)

    db.commit()
    return {"status": "deleted", "removed": len(observations)}


@router.post("/upload/{airbase_id}", response_model=ObservationOut)
async def upload_observation(
    airbase_id: int,
    observation_date: str,
    file: UploadFile = File(...),
    source: str = "manual",
    db: Session = Depends(get_db),
):
    """Upload a satellite image and run aircraft detection."""
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")

    # Save image
    storage_dir = Path(settings.image_storage_path) / airbase.name.replace(" ", "_")
    storage_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{observation_date}_{file.filename}"
    image_path = storage_dir / filename
    content = await file.read()
    with open(image_path, "wb") as f:
        f.write(content)

    # Create observation
    obs = Observation(
        airbase_id=airbase_id,
        observation_date=datetime.fromisoformat(observation_date),
        image_path=str(image_path),
        source=source,
    )
    db.add(obs)
    db.flush()

    # Run two-stage detection pipeline
    detections = detection_service.detect(str(image_path), airbase_name=airbase.name, country=airbase.country, known_units=airbase.known_units)
    for det in detections:
        db.add(
            Detection(
                observation_id=obs.id,
                aircraft_type=det.aircraft_type,
                confidence=det.confidence,
                bbox_x=det.bbox_x,
                bbox_y=det.bbox_y,
                bbox_w=det.bbox_w,
                bbox_h=det.bbox_h,
            )
        )

    db.commit()
    db.refresh(obs)
    return obs
