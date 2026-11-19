import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db
from app.models.airbase import Airbase, CaptureZone, Observation, Detection
from app.services.tiles import tile_service
from app.services.detection import detection_service
from app.config import settings

logger = logging.getLogger("vauban.bulk")

router = APIRouter(prefix="/api/bulk", tags=["bulk"])


@router.post("/capture")
async def bulk_capture(
    country: str = None,
    db: Session = Depends(get_db),
):
    """Capture all zones for all airbases (or by country)."""
    query = db.query(Airbase)
    if country:
        query = query.filter(Airbase.country == country)
    airbases = query.all()

    logger.info(f"Bulk capture: {len(airbases)} airbases" + (f" ({country})" if country else ""))

    results = []
    for airbase in airbases:
        zones = airbase.capture_zones
        if not zones:
            # Default: single capture at base center
            zones = [CaptureZone(
                label="default", latitude=airbase.latitude,
                longitude=airbase.longitude, zoom=17, grid_size=6,
            )]

        base_detections = 0
        base_zones_ok = 0

        for zone in zones:
            try:
                image_path, img_w, img_h = await tile_service.fetch_area(
                    latitude=zone.latitude,
                    longitude=zone.longitude,
                    airbase_name=airbase.name,
                    zoom=zone.zoom,
                    grid_size=zone.grid_size,
                    zone_label=zone.label,
                )

                obs = Observation(
                    airbase_id=airbase.id,
                    observation_date=datetime.now(),
                    image_path=str(image_path),
                    source=f"esri-z{zone.zoom}",
                    zone_id=zone.id if zone.id else None,
                    zone_label=zone.label,
                    image_width=img_w,
                    image_height=img_h,
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
                base_detections += len(detections)
                base_zones_ok += 1

            except Exception as e:
                logger.warning(f"  {airbase.name}/{zone.label}: FAILED - {e}")

        results.append({
            "airbase_id": airbase.id,
            "airbase_name": airbase.name,
            "status": "ok" if base_zones_ok > 0 else "error",
            "zones_captured": base_zones_ok,
            "zones_total": len(zones),
            "aircraft_count": base_detections,
        })
        logger.info(f"  {airbase.name}: {base_zones_ok}/{len(zones)} zones, {base_detections} det")

    succeeded = sum(1 for r in results if r["status"] == "ok")
    return {
        "total": len(airbases),
        "succeeded": succeeded,
        "failed": len(airbases) - succeeded,
        "results": results,
    }
