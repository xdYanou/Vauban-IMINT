import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.database import get_db
from app.models.airbase import Airbase, CaptureZone, Observation, Detection
from app.services.tiles import tile_service, TILE_SOURCES
from app.services.detection import detection_service
from app.config import settings

logger = logging.getLogger("vauban.tiles.api")

router = APIRouter(prefix="/api/tiles", tags=["tiles"])

# Mock dates: each tile source = different "observation date"
SOURCE_MOCK_DATES = {"esri": 0, "google": -7, "bing": -14}
SOURCE_LABELS = {"esri": "Esri Imagery", "google": "Google Imagery", "bing": "Bing Imagery"}


def _get_mock_date(source: str) -> datetime:
    today = datetime.now()
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    offset = SOURCE_MOCK_DATES.get(source, 0)
    return this_monday + timedelta(days=offset)


async def _capture_zones(airbase, zones, source, db):
    """Capture all zones from a single source. Returns results list."""
    mock_date = _get_mock_date(source)
    zone_results = []
    total = 0

    for zone in zones:
        try:
            image_path, img_w, img_h = await tile_service.fetch_area(
                latitude=zone.latitude, longitude=zone.longitude,
                airbase_name=airbase.name, zoom=zone.zoom,
                grid_size=zone.grid_size, zone_label=zone.label,
                source=source,
            )
            obs = Observation(
                airbase_id=airbase.id, observation_date=mock_date,
                image_path=str(image_path), source=f"{source}*",
                zone_id=zone.id, zone_label=zone.label,
                image_width=img_w, image_height=img_h,
            )
            db.add(obs)
            db.flush()

            try:
                detections = detection_service.detect(
                    str(image_path), airbase_name=airbase.name,
                    country=airbase.country, known_units=airbase.known_units,
                )
            except Exception:
                detections = []

            for det in detections:
                db.add(Detection(
                    observation_id=obs.id, aircraft_type=det.aircraft_type,
                    confidence=det.confidence, bbox_x=det.bbox_x,
                    bbox_y=det.bbox_y, bbox_w=det.bbox_w, bbox_h=det.bbox_h,
                ))
            db.commit()

            relative_path = str(image_path).replace(settings.image_storage_path, "").lstrip("/")
            total += len(detections)
            zone_results.append({
                "zone_label": zone.label, "observation_id": obs.id,
                "image_url": f"/images/{relative_path}",
                "image_size": [img_w, img_h], "zoom": zone.zoom,
                "aircraft_count": len(detections),
                "detections": [
                    {"type": d.aircraft_type, "confidence": d.confidence,
                     "bbox": [d.bbox_x, d.bbox_y, d.bbox_w, d.bbox_h]}
                    for d in detections
                ],
            })
        except Exception as e:
            logger.warning(f"{source}/{zone.label}: {e}")

    return zone_results, total, mock_date


def _get_zones(airbase):
    zones = airbase.capture_zones
    if not zones:
        return [CaptureZone(
            id=None, airbase_id=airbase.id, label="default",
            latitude=airbase.latitude, longitude=airbase.longitude,
            zoom=17, grid_size=6,
        )]
    return zones


@router.post("/fetch/{airbase_id}")
async def fetch_single_source(
    airbase_id: int,
    source: str = "esri",
    db: Session = Depends(get_db),
):
    """Capture all zones from one tile source."""
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")

    zones = _get_zones(airbase)
    logger.info(f"Capturing {airbase.name}: {len(zones)} zones [{source}]")

    zone_results, total, mock_date = await _capture_zones(airbase, zones, source, db)

    type_counts = {}
    for zr in zone_results:
        for d in zr.get("detections", []):
            type_counts[d["type"]] = type_counts.get(d["type"], 0) + 1

    return {
        "airbase": airbase.name, "source": source,
        "mock_date": mock_date.strftime("%Y-%m-%d"),
        "zones_captured": len(zone_results),
        "total_aircraft": total,
        "aircraft_types": type_counts,
        "zones": zone_results,
    }


@router.post("/fetch-multi/{airbase_id}")
async def fetch_multi_source(
    airbase_id: int,
    db: Session = Depends(get_db),
):
    """
    Capture from all 3 tile sources (Esri, Google, Bing).
    Each stored as a separate observation with a mock date (consecutive Mondays).
    Gives 3 temporal data points for change detection analytics.

    * Dates are simulated — each source represents a different capture date.
    """
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")

    zones = _get_zones(airbase)
    logger.info(f"Multi-source capture {airbase.name}: {len(zones)} zones x 3 sources")

    captures = []
    for source_name in TILE_SOURCES.keys():
        zone_results, total, mock_date = await _capture_zones(airbase, zones, source_name, db)

        type_counts = {}
        for zr in zone_results:
            for d in zr.get("detections", []):
                type_counts[d["type"]] = type_counts.get(d["type"], 0) + 1

        captures.append({
            "source": source_name,
            "label": SOURCE_LABELS.get(source_name, source_name),
            "mock_date": mock_date.strftime("%Y-%m-%d"),
            "total_aircraft": total,
            "aircraft_types": type_counts,
            "zones": zone_results,
        })
        logger.info(f"  {source_name}: {total} aircraft [{mock_date.strftime('%Y-%m-%d')}]")

    return {
        "airbase": airbase.name,
        "captures": captures,
        "note": "* Dates are simulated. Each source represents imagery from a different capture date.",
    }
