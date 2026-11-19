"""
Single-stage aircraft detection and classification using YOLOv8.

The model detects aircraft in satellite imagery and classifies them directly
into specific types (Su-35, Tu-95, F-16, etc.) — no separate classifier needed.

Model versions:
  v1: 7 broad categories (fighter, bomber, transport, etc.)
  v2: 20 specific types (Su-35, Tu-160, B-52, F-22, etc.) ← current
"""
import logging
from pathlib import Path
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("vauban.detection")


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
        """Load YOLOv8 model. Prefers v2 (20 types) over v1 (7 categories)."""
        from ultralytics import YOLO

        model_dir = Path(settings.model_storage_path)

        # Try v2 first (20 real types), then v1, then pretrained fallback
        for name in ["vauban_detect_v2.pt", "vauban_detect_v1.pt"]:
            path = model_dir / name
            if path.exists():
                self.model = YOLO(str(path))
                logger.info(f"Loaded model: {path}")
                return

        self.model = YOLO("yolov8n.pt")
        logger.info("No trained model found — using pretrained COCO fallback")

    def detect(self, image_path: str) -> list[DetectionResult]:
        """Run detection on a satellite image."""
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

                # Get type name from model
                if self.model.names and cls_id in self.model.names:
                    aircraft_type = self.model.names[cls_id]
                elif cls_id == 4:
                    # COCO fallback: class 4 = airplane
                    aircraft_type = "aircraft"
                else:
                    continue  # Skip non-aircraft COCO classes

                detections.append(DetectionResult(
                    aircraft_type=aircraft_type,
                    confidence=conf,
                    bbox_x=cx,
                    bbox_y=cy,
                    bbox_w=w,
                    bbox_h=h,
                ))

        return detections


detection_service = DetectionService()
