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
    zoom: int = None,
    radius_km: float = None,
    full_base: bool = False,
    db: Session = Depends(get_db),
):
    """
    Fetch high-resolution satellite imagery and run detection.

    If zoom/radius not specified, uses the airbase's configured values.
    Set full_base=true for multi-zone capture of large facilities.
    """
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")

    z = zoom or airbase.capture_zoom or 17
    r = radius_km or airbase.capture_radius_km or 1.5

    logger.info(f"Capture {airbase.name}: z{z}, {r}km radius, full_base={full_base}")

    try:
        if full_base:
            captures = await tile_service.fetch_full_base(
                latitude=airbase.latitude,
                longitude=airbase.longitude,
                airbase_name=airbase.name,
                zoom=z,
                radius_km=r,
            )
        else:
            path, w, h = await tile_service.fetch_area(
                latitude=airbase.latitude,
                longitude=airbase.longitude,
                airbase_name=airbase.name,
                zoom=z,
                radius_km=r,
            )
            captures = [(path, w, h, None)]
    except Exception as e:
        logger.exception(f"Tile fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch imagery: {e}")

    all_results = []

    for image_path, img_w, img_h, zone_label in captures:
        obs = Observation(
            airbase_id=airbase_id,
            observation_date=datetime.now(),
            image_path=str(image_path),
            source=f"esri-z{z}",
            zone=zone_label,
            image_width=img_w,
            image_height=img_h,
        )
        db.add(obs)
        db.flush()

        try:
            detections = detection_service.detect(str(image_path))
        except Exception as e:
            logger.warning(f"Detection failed for {zone_label}: {e}")
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

        relative_path = str(image_path).replace(settings.image_storage_path, "").lstrip("/")

        all_results.append({
            "observation_id": obs.id,
            "image_url": f"/images/{relative_path}",
            "zone": zone_label,
            "image_size": [img_w, img_h],
            "aircraft_count": len(detections),
            "detections": [
                {
                    "type": d.aircraft_type,
                    "broad_category": d.broad_category,
                    "confidence": d.confidence,
                }
                for d in detections
            ],
        })

    total_aircraft = sum(r["aircraft_count"] for r in all_results)
    logger.info(f"{airbase.name}: {len(all_results)} zones, {total_aircraft} total detections")

    return {
        "airbase": airbase.name,
        "zoom": z,
        "radius_km": r,
        "zones": all_results,
        "total_aircraft": total_aircraft,
    }
