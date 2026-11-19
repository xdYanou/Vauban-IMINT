import logging
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.database import get_db
from app.models.airbase import Airbase, Observation, Detection
from app.config import settings

logger = logging.getLogger("vauban.analytics")

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _group_into_captures(observations):
    """
    Group observations into capture sessions.
    Observations within 60 seconds of each other = same capture.
    Returns list of captures, each with aggregated data.
    """
    if not observations:
        return []

    captures = []
    current_group = [observations[0]]

    for obs in observations[1:]:
        prev = current_group[-1]
        diff = abs((obs.observation_date - prev.observation_date).total_seconds())
        if diff < 60:
            current_group.append(obs)
        else:
            captures.append(current_group)
            current_group = [obs]
    captures.append(current_group)

    results = []
    for group in captures:
        type_counts = {}
        all_detections = []
        images = []

        for obs in group:
            for det in obs.detections:
                type_counts[det.aircraft_type] = type_counts.get(det.aircraft_type, 0) + 1
                all_detections.append({
                    "id": det.id,
                    "aircraft_type": det.aircraft_type,
                    "confidence": det.confidence,
                    "bbox": [det.bbox_x, det.bbox_y, det.bbox_w, det.bbox_h],
                })

            relative_path = obs.image_path.replace(settings.image_storage_path, "").lstrip("/")
            zone_detections = [{
                "id": det.id,
                "aircraft_type": det.aircraft_type,
                "confidence": det.confidence,
                "bbox": [det.bbox_x, det.bbox_y, det.bbox_w, det.bbox_h],
            } for det in obs.detections]

            images.append({
                "observation_id": obs.id,
                "image_url": f"/images/{relative_path}",
                "zone_label": obs.zone_label,
                "source": obs.source,
                "detections": zone_detections,
            })

        total = sum(type_counts.values())
        results.append({
            "date": group[0].observation_date.isoformat(),
            "source": group[0].source,
            "zones": len(group),
            "total_aircraft": total,
            "aircraft_types": type_counts,
            "detections": all_detections,
            "images": images,
        })

    return results


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """Global platform stats."""
    total_airbases = db.query(Airbase).count()
    total_observations = db.query(Observation).count()
    total_detections = db.query(Detection).count()

    active_bases = (
        db.query(Airbase.id, Airbase.name, func.count(Observation.id).label("obs_count"))
        .join(Observation)
        .group_by(Airbase.id)
        .order_by(desc("obs_count"))
        .limit(10)
        .all()
    )

    type_dist = (
        db.query(Detection.aircraft_type, func.count(Detection.id).label("count"))
        .group_by(Detection.aircraft_type)
        .order_by(desc("count"))
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
    }


@router.get("/airbase/{airbase_id}/timeline")
def get_airbase_timeline(airbase_id: int, db: Session = Depends(get_db)):
    """Historical captures for an airbase, grouped by session."""
    observations = (
        db.query(Observation)
        .filter(Observation.airbase_id == airbase_id)
        .order_by(Observation.observation_date.asc())
        .all()
    )
    return _group_into_captures(observations)


@router.get("/airbase/{airbase_id}/summary")
def get_airbase_summary(airbase_id: int, db: Session = Depends(get_db)):
    """Quick summary stats for an airbase."""
    observations = (
        db.query(Observation)
        .filter(Observation.airbase_id == airbase_id)
        .order_by(Observation.observation_date.asc())
        .all()
    )

    captures = _group_into_captures(observations)
    total_det = sum(c["total_aircraft"] for c in captures)

    latest = captures[-1] if captures else None

    return {
        "capture_count": len(captures),
        "total_detections": total_det,
        "latest": latest,
    }
