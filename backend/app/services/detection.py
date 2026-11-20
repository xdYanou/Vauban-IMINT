"""
Aircraft detection with base-context classification.

Stage 1: YOLOv8 detects aircraft and gives a raw classification (trained on US types).
Stage 2: Base-context override — uses known order of battle to reclassify detections
         based on what aircraft are actually stationed at each base.

The model is good at detecting aircraft shapes and distinguishing size classes
(fighter vs bomber vs transport). The context override maps those shape classes
to the correct types for non-US bases.
"""
import json
import logging
from pathlib import Path
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("vauban.detection")

# Map model output types to shape categories for context matching
SHAPE_CATEGORY = {
    # Fighters (small, single/twin engine)
    "Su-35": "fighter", "F-15": "fighter", "F-16": "fighter",
    "F-22": "fighter", "FA-18": "fighter",
    # Bombers (large, swept/variable wing)
    "B-52": "heavy_bomber", "B-1B": "swing_bomber", "Tu-95": "heavy_bomber",
    "Tu-160": "swing_bomber", "Tu-22M": "medium_bomber",
    # Attack/Strike
    "Su-34": "strike", "Su-24": "strike",
    # Transport
    "C-130": "medium_transport", "C-17": "heavy_transport", "C-5": "heavy_transport",
    "KC-135": "tanker", "KC-10": "tanker",
    # ISR
    "E-3": "awacs", "E-8": "awacs", "P-3C": "patrol",
    # Generic
    "aircraft": "unknown",
}

# Base context: what shape categories map to at each base's country/known units
# This is loaded from a JSON file so it can be edited without code changes
_BASE_CONTEXT = None

def _load_base_context():
    global _BASE_CONTEXT
    path = Path(__file__).parent.parent / "data" / "base_context.json"
    if path.exists():
        with open(path) as f:
            _BASE_CONTEXT = json.load(f)
    else:
        _BASE_CONTEXT = {}
    return _BASE_CONTEXT


def reclassify_for_base(detections: list, airbase_name: str, known_units: str = "") -> list:
    """
    Override model classifications using base context.

    Uses the shape category (fighter/bomber/transport) from the model detection
    and maps it to the actual aircraft type known to be at this base.
    """
    ctx = _load_base_context()

    # Check for base-specific overrides first, then country-level
    base_map = ctx.get(airbase_name, {})

    if not base_map:
        # No context for this base — return raw detections
        return detections

    reclassified = []
    for det in detections:
        shape = SHAPE_CATEGORY.get(det.aircraft_type, "unknown")

        # Look up what this shape category means at this base
        new_type = base_map.get(shape)

        if new_type:
            reclassified.append(DetectionResult(
                aircraft_type=new_type,
                confidence=det.confidence,
                bbox_x=det.bbox_x,
                bbox_y=det.bbox_y,
                bbox_w=det.bbox_w,
                bbox_h=det.bbox_h,
            ))
        else:
            # No mapping — keep original
            reclassified.append(det)

    return reclassified


@dataclass
class DetectionResult:
    aircraft_type: str
    confidence: float
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float


class DetectionService:
    def __init__(self):
        self.model = None

    def load_model(self):
        """Load YOLOv8 model."""
        from ultralytics import YOLO

        model_dir = Path(settings.model_storage_path)

        for name in ["vauban_detect_v2.pt", "vauban_detect_v1.pt"]:
            path = model_dir / name
            if path.exists():
                self.model = YOLO(str(path))
                logger.info(f"Loaded model: {path}")
                return

        self.model = YOLO("yolov8n.pt")
        logger.info("No trained model found — using pretrained COCO fallback")

    def detect(self, image_path: str, airbase_name: str = None, known_units: str = None) -> list[DetectionResult]:
        """
        Run detection on a satellite image.

        If airbase_name is provided, applies base-context reclassification.
        """
        if self.model is None:
            self.load_model()

        results = self.model(image_path, conf=settings.detection_confidence_threshold, imgsz=1280)
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i in range(len(boxes)):
                box = boxes[i]
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                cx, cy, w, h = box.xywh[0].tolist()

                if self.model.names and cls_id in self.model.names:
                    aircraft_type = self.model.names[cls_id]
                elif cls_id == 4:
                    aircraft_type = "aircraft"
                else:
                    continue

                detections.append(DetectionResult(
                    aircraft_type=aircraft_type,
                    confidence=conf,
                    bbox_x=cx,
                    bbox_y=cy,
                    bbox_w=w,
                    bbox_h=h,
                ))

        # Apply base context reclassification
        if airbase_name:
            detections = reclassify_for_base(detections, airbase_name, known_units or "")

        return detections


detection_service = DetectionService()
