import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.models.database import get_db
from app.models.airbase import Airbase, Observation, Detection
from app.services.sentinel import sentinel_service
from app.services.detection import detection_service

logger = logging.getLogger("vauban.sentinel.api")

router = APIRouter(prefix="/api/sentinel", tags=["sentinel"])


@router.post("/fetch/{airbase_id}")
async def fetch_and_analyze(
    airbase_id: int,
    date_from: str,
    date_to: str,
    db: Session = Depends(get_db),
):
    """
    Fetch Sentinel-2 image via Process API for a date range, run detection, save observation.
    The Process API automatically picks the best (most recent, least cloudy) image available.
    """
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")

    logger.info(f"Fetch request for {airbase.name} ({date_from} to {date_to})")

    try:
        image_path = await sentinel_service.fetch_image(
            latitude=airbase.latitude,
            longitude=airbase.longitude,
            date_from=date_from,
            date_to=date_to,
            airbase_name=airbase.name,
        )
    except Exception as e:
        logger.exception(f"Failed to fetch image: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch Sentinel image: {e}")

    # Check if the image is not empty (all black = no data for this area/period)
    from PIL import Image
    import numpy as np
    img = Image.open(image_path)
    arr = np.array(img)
    if arr.max() == 0:
        image_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=404,
            detail="No imagery available for this airbase in the selected period. Try a different date range."
        )

    # Create observation
    obs = Observation(
        airbase_id=airbase_id,
        observation_date=datetime.strptime(date_from, "%Y-%m-%d"),
        image_path=str(image_path),
        source="sentinel-2",
    )
    db.add(obs)
    db.flush()

    # Run two-stage detection pipeline
    try:
        detections = detection_service.detect(str(image_path), airbase_name=airbase.name, country=airbase.country, known_units=airbase.known_units)
    except Exception as e:
        logger.exception(f"Detection failed: {e}")
        detections = []

    for det in detections:
        db.add(Detection(
            observation_id=obs.id,
            aircraft_type=det.aircraft_type,
            confidence=det.confidence,
            bbox_x=det.bbox_x,
            bbox_y=det.bbox_y,
            bbox_w=det.bbox_w,
            bbox_h=det.bbox_h,
        ))

    db.commit()
    db.refresh(obs)

    logger.info(f"Observation {obs.id} created: {len(detections)} detections")

    # Build browser-accessible image URL
    from app.config import settings
    relative_path = str(image_path).replace(settings.image_storage_path, "").lstrip("/")
    image_url = f"/images/{relative_path}"

    return {
        "observation_id": obs.id,
        "image_url": image_url,
        "aircraft_count": len(detections),
        "detections": [
            {
                "type": d.aircraft_type,
                "confidence": d.confidence,
                "bbox": [d.bbox_x, d.bbox_y, d.bbox_w, d.bbox_h],
            }
            for d in detections
        ],
    }
