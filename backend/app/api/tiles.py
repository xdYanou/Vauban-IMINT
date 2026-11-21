import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db
from app.models.airbase import Airbase, CaptureZone, Observation, Detection
from app.services.tiles import tile_service
from app.services.detection import detection_service
from app.config import settings

logger = logging.getLogger("vauban.tiles.api")

router = APIRouter(prefix="/api/tiles", tags=["tiles"])


@router.post("/fetch/{airbase_id}")
async def fetch_all_zones(
    airbase_id: int,
    db: Session = Depends(get_db),
):
    """
    Capture all defined zones for an airbase and run detection.
    If no zones defined, falls back to a single capture at the base coordinates.
    Aggregates detection counts across all zones.
    """
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")

    zones = airbase.capture_zones
    if not zones:
        # Fallback: single capture at base coords with defaults
        zones = [CaptureZone(
            id=None, airbase_id=airbase_id, label="default",
            latitude=airbase.latitude, longitude=airbase.longitude,
            zoom=17, grid_size=6,
        )]

    logger.info(f"Capturing {airbase.name}: {len(zones)} zones")

    zone_results = []
    total_detections = 0

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
                airbase_id=airbase_id,
                observation_date=datetime.now(),
                image_path=str(image_path),
                source=f"esri-z{zone.zoom}",
                zone_id=zone.id,
                zone_label=zone.label,
                image_width=img_w,
                image_height=img_h,
            )
            db.add(obs)
            db.flush()

            try:
                detections = detection_service.detect(str(image_path), airbase_name=airbase.name, country=airbase.country, known_units=airbase.known_units)
            except Exception as e:
                logger.warning(f"Detection failed for zone {zone.label}: {e}")
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

            relative_path = str(image_path).replace(settings.image_storage_path, "").lstrip("/")
            total_detections += len(detections)

            zone_results.append({
                "zone_id": zone.id,
                "zone_label": zone.label,
                "observation_id": obs.id,
                "image_url": f"/images/{relative_path}",
                "image_size": [img_w, img_h],
                "zoom": zone.zoom,
                "aircraft_count": len(detections),
                "detections": [
                    {
                        "type": d.aircraft_type,
                        "confidence": d.confidence,
                        "bbox": [d.bbox_x, d.bbox_y, d.bbox_w, d.bbox_h],
                    }
                    for d in detections
                ],
            })
            logger.info(f"  {zone.label}: {len(detections)} detections")

        except Exception as e:
            logger.warning(f"  Zone {zone.label} failed: {e}")
            zone_results.append({
                "zone_label": zone.label,
                "status": "error",
                "error": str(e),
            })

    # Aggregate type counts across all zones
    type_counts = {}
    for zr in zone_results:
        for d in zr.get("detections", []):
            t = d["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "airbase": airbase.name,
        "zones_captured": len(zone_results),
        "total_aircraft": total_detections,
        "aircraft_types": type_counts,
        "zones": zone_results,
    }
