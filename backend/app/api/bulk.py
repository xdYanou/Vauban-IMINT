import logging
import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db
from app.models.airbase import Airbase, Observation, Detection
from app.services.tiles import tile_service
from app.services.detection import detection_service
from app.config import settings

logger = logging.getLogger("vauban.bulk")

router = APIRouter(prefix="/api/bulk", tags=["bulk"])


@router.post("/capture")
async def bulk_capture(
    zoom: int = 17,
    grid_size: int = 6,
    db: Session = Depends(get_db),
):
    """
    Capture high-res imagery for ALL airbases in one go.
    Returns progress and results for each base.
    """
    airbases = db.query(Airbase).all()
    logger.info(f"Bulk capture started: {len(airbases)} airbases at zoom {zoom}")

    results = []
    for airbase in airbases:
        try:
            image_path = await tile_service.fetch_area(
                latitude=airbase.latitude,
                longitude=airbase.longitude,
                airbase_name=airbase.name,
                zoom=zoom,
                grid_size=grid_size,
            )

            obs = Observation(
                airbase_id=airbase.id,
                observation_date=datetime.now(),
                image_path=str(image_path),
                source=f"esri-z{zoom}",
            )
            db.add(obs)
            db.flush()

            try:
                detections = detection_service.detect(str(image_path))
            except Exception:
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

            results.append({
                "airbase_id": airbase.id,
                "airbase_name": airbase.name,
                "status": "ok",
                "observation_id": obs.id,
                "image_url": f"/images/{relative_path}",
                "aircraft_count": len(detections),
            })
            logger.info(f"  {airbase.name}: {len(detections)} detections")

        except Exception as e:
            logger.warning(f"  {airbase.name}: FAILED - {e}")
            results.append({
                "airbase_id": airbase.id,
                "airbase_name": airbase.name,
                "status": "error",
                "error": str(e),
            })

    succeeded = sum(1 for r in results if r["status"] == "ok")
    logger.info(f"Bulk capture done: {succeeded}/{len(airbases)} succeeded")

    return {
        "total": len(airbases),
        "succeeded": succeeded,
        "failed": len(airbases) - succeeded,
        "results": results,
    }
