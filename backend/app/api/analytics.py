import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.database import get_db
from app.models.airbase import Airbase, Observation, Detection

logger = logging.getLogger("vauban.analytics")

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """Global platform stats."""
    total_airbases = db.query(Airbase).count()
    total_observations = db.query(Observation).count()
    total_detections = db.query(Detection).count()

    # Airbases with most observations
    active_bases = (
        db.query(Airbase.id, Airbase.name, func.count(Observation.id).label("obs_count"))
        .join(Observation)
        .group_by(Airbase.id)
        .order_by(desc("obs_count"))
        .limit(10)
        .all()
    )

    # Aircraft type distribution across all detections
    type_dist = (
        db.query(Detection.aircraft_type, func.count(Detection.id).label("count"))
        .group_by(Detection.aircraft_type)
        .order_by(desc("count"))
        .all()
    )

    # Recent observations
    recent = (
        db.query(Observation)
        .order_by(Observation.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_airbases": total_airbases,
        "total_observations": total_observations,
        "total_detections": total_detections,
        "active_bases": [
            {"id": b.id, "name": b.name, "observation_count": b.obs_count}
            for b in active_bases
        ],
        "aircraft_type_distribution": {t.aircraft_type: t.count for t in type_dist},
        "recent_observations": [
            {
                "id": o.id,
                "airbase_id": o.airbase_id,
                "date": o.observation_date.isoformat(),
                "source": o.source,
                "detection_count": len(o.detections),
            }
            for o in recent
        ],
    }


@router.get("/airbase/{airbase_id}/timeline")
def get_airbase_timeline(airbase_id: int, db: Session = Depends(get_db)):
    """Historical observation data for an airbase — for charts."""
    observations = (
        db.query(Observation)
        .filter(Observation.airbase_id == airbase_id)
        .order_by(Observation.observation_date.asc())
        .all()
    )

    timeline = []
    for obs in observations:
        type_counts = {}
        for det in obs.detections:
            type_counts[det.aircraft_type] = type_counts.get(det.aircraft_type, 0) + 1

        from app.config import settings
        relative_path = obs.image_path.replace(settings.image_storage_path, "").lstrip("/")

        timeline.append({
            "id": obs.id,
            "date": obs.observation_date.isoformat(),
            "source": obs.source,
            "cloud_cover_pct": obs.cloud_cover_pct,
            "image_url": f"/images/{relative_path}",
            "total_aircraft": len(obs.detections),
            "aircraft_types": type_counts,
            "detections": [
                {
                    "id": d.id,
                    "aircraft_type": d.aircraft_type,
                    "broad_category": d.broad_category,
                    "confidence": d.confidence,
                    "classification_conf": d.classification_conf,
                    "bbox": [d.bbox_x, d.bbox_y, d.bbox_w, d.bbox_h],
                }
                for d in obs.detections
            ],
        })

    return timeline


@router.get("/airbase/{airbase_id}/summary")
def get_airbase_summary(airbase_id: int, db: Session = Depends(get_db)):
    """Quick summary stats for an airbase."""
    obs_count = db.query(Observation).filter(Observation.airbase_id == airbase_id).count()
    det_count = (
        db.query(Detection)
        .join(Observation)
        .filter(Observation.airbase_id == airbase_id)
        .count()
    )

    # Latest observation
    latest = (
        db.query(Observation)
        .filter(Observation.airbase_id == airbase_id)
        .order_by(Observation.observation_date.desc())
        .first()
    )

    latest_data = None
    if latest:
        type_counts = {}
        for d in latest.detections:
            type_counts[d.aircraft_type] = type_counts.get(d.aircraft_type, 0) + 1

        from app.config import settings
        relative_path = latest.image_path.replace(settings.image_storage_path, "").lstrip("/")

        latest_data = {
            "id": latest.id,
            "date": latest.observation_date.isoformat(),
            "source": latest.source,
            "image_url": f"/images/{relative_path}",
            "total_aircraft": len(latest.detections),
            "aircraft_types": type_counts,
        }

    return {
        "observation_count": obs_count,
        "total_detections": det_count,
        "latest": latest_data,
    }
