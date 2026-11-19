import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db
from app.models.airbase import Airbase, Observation, Detection
from app.services.tiles import tile_service
from app.services.detection import detection_service
from app.config import settings

logger = logging.getLogger("vauban.tiles.api")

router = APIRouter(prefix="/api/tiles", tags=["tiles"])


@router.post("/fetch/{airbase_id}")
async def fetch_highres(
    airbase_id: int,
    zoom: int = 17,
    grid_size: int = 6,
    db: Session = Depends(get_db),
):
    """
    Fetch high-resolution satellite imagery from tile server and run detection.

    zoom: 17 = ~1.2m/px, 18 = ~0.6m/px (best for aircraft detection)
    grid_size: tiles per side (6x6 = 1536x1536px)
    """
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")

    logger.info(f"High-res fetch for {airbase.name} at zoom {zoom}")

    try:
        image_path = await tile_service.fetch_area(
            latitude=airbase.latitude,
            longitude=airbase.longitude,
            airbase_name=airbase.name,
            zoom=zoom,
            grid_size=grid_size,
        )
    except Exception as e:
        logger.exception(f"Tile fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch imagery: {e}")

    # Create observation
    obs = Observation(
        airbase_id=airbase_id,
        observation_date=datetime.now(),
        image_path=str(image_path),
        source=f"esri-z{zoom}",
    )
    db.add(obs)
    db.flush()

    # Run detection
    try:
        detections = detection_service.detect(str(image_path))
    except Exception as e:
        logger.exception(f"Detection failed: {e}")
        detections = []

    for det in detections:
        db.add(Detection(
            observation_id=obs.id,
            aircraft_type=det.aircraft_type,
            broad_category=det.broad_category,
            confidence=det.confidence,
            classification_conf=det.classification_conf,
            bbox_x=det.bbox_x,
            bbox_y=det.bbox_y,
            bbox_w=det.bbox_w,
            bbox_h=det.bbox_h,
        ))

    db.commit()
    db.refresh(obs)

    # Build image URL
    relative_path = str(image_path).replace(settings.image_storage_path, "").lstrip("/")
    image_url = f"/images/{relative_path}"

    logger.info(f"Observation {obs.id}: {len(detections)} detections")

    return {
        "observation_id": obs.id,
        "image_url": image_url,
        "aircraft_count": len(detections),
        "zoom": zoom,
        "detections": [
            {
                "type": d.aircraft_type,
                "broad_category": d.broad_category,
                "confidence": d.confidence,
            }
            for d in detections
        ],
    }
