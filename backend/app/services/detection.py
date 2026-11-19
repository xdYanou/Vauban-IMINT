"""
Two-stage aircraft detection and classification pipeline.

Stage 1 (YOLO): Detect aircraft in satellite imagery → bounding boxes + broad category
  Classes: fighter, bomber, transport, tanker, surveillance, rotary, trainer

Stage 2 (EfficientNet classifier): Crop each detection → classify specific type
  Classes: Su-24, Su-34, Tu-95, MiG-31, etc. (35 types)

The pipeline runs both stages automatically. If Stage 2 model isn't available,
it falls back to Stage 1 broad categories only.
"""
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import torch
from PIL import Image
from torchvision import transforms, models
import torch.nn as nn

from app.config import settings

# Stage 1: YOLO broad detection classes
DETECTOR_CLASSES = ["fighter", "bomber", "transport", "tanker", "surveillance", "rotary", "trainer"]

# Stage 2: Fine-grained classifier classes (set at load time from checkpoint)
CLASSIFIER_CLASSES = None


@dataclass
class DetectionResult:
    aircraft_type: str        # Fine-grained type (e.g. "Su-34") or broad category
    broad_category: str       # Always the Stage 1 broad category
    confidence: float         # Stage 1 detection confidence
    classification_conf: float | None  # Stage 2 classification confidence (None if not run)
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float


class DetectionService:
    def __init__(self):
        self.detector = None       # Stage 1: YOLOv8
        self.classifier = None     # Stage 2: EfficientNet
        self.classifier_classes = None
        self.classifier_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        self.device = None

    def _get_device(self):
        if self.device is None:
            if torch.backends.mps.is_available():
                self.device = torch.device("mps")
            elif torch.cuda.is_available():
                self.device = torch.device("cuda")
            else:
                self.device = torch.device("cpu")
        return self.device

    def load_detector(self):
        """Load Stage 1: YOLOv8 aircraft detector."""
        from ultralytics import YOLO

        # Prefer our fine-tuned model, fall back to pretrained
        model_path = Path(settings.model_storage_path) / "vauban_detect_v1.pt"
        if model_path.exists():
            self.detector = YOLO(str(model_path))
            print(f"Loaded fine-tuned detector: {model_path}")
        else:
            fallback = Path(settings.model_storage_path) / settings.detection_model_name
            if fallback.exists():
                self.detector = YOLO(str(fallback))
            else:
                self.detector = YOLO("yolov8n.pt")
            print("Loaded pretrained YOLO (no fine-tuned detector yet)")

    def load_classifier(self):
        """Load Stage 2: Fine-grained aircraft classifier."""
        model_path = Path(settings.model_storage_path) / "vauban_classifier_v1.pt"
        if not model_path.exists():
            print("No classifier model found — Stage 2 disabled, using broad categories only")
            return

        device = self._get_device()
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)

        self.classifier_classes = checkpoint["classes"]
        num_classes = checkpoint["num_classes"]

        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        model = model.to(device)

        self.classifier = model
        print(f"Loaded classifier: {num_classes} classes, best_val_acc={checkpoint.get('best_val_acc', 'N/A')}")

    def _classify_crop(self, crop: Image.Image) -> tuple[str, float]:
        """Run Stage 2 classifier on a single cropped aircraft image."""
        if self.classifier is None:
            return None, None

        device = self._get_device()
        tensor = self.classifier_transform(crop).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = self.classifier(tensor)
            probs = torch.softmax(outputs, dim=1)
            conf, pred = probs.max(1)

        class_name = self.classifier_classes[pred.item()]
        return class_name, conf.item()

    def _extract_crop(self, image: Image.Image, cx: float, cy: float, w: float, h: float, padding: float = 0.1) -> Image.Image:
        """Extract a crop from the image with some padding."""
        img_w, img_h = image.size
        pad_w = w * padding
        pad_h = h * padding

        x1 = max(0, int(cx - w / 2 - pad_w))
        y1 = max(0, int(cy - h / 2 - pad_h))
        x2 = min(img_w, int(cx + w / 2 + pad_w))
        y2 = min(img_h, int(cy + h / 2 + pad_h))

        return image.crop((x1, y1, x2, y2))

    def detect(self, image_path: str) -> list[DetectionResult]:
        """
        Run the full two-stage pipeline on a satellite image.

        Stage 1: YOLO detects aircraft → bounding boxes + broad category
        Stage 2: Classifier refines each detection → specific aircraft type
        """
        if self.detector is None:
            self.load_detector()
            self.load_classifier()

        # Stage 1: Detection
        results = self.detector(image_path, conf=settings.detection_confidence_threshold)
        image = Image.open(image_path).convert("RGB")

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i in range(len(boxes)):
                box = boxes[i]
                cls_id = int(box.cls[0])
                det_conf = float(box.conf[0])
                cx, cy, w, h = box.xywh[0].tolist()

                # Map detector class
                if self.detector.names and cls_id in self.detector.names:
                    broad_category = self.detector.names[cls_id]
                elif cls_id < len(DETECTOR_CLASSES):
                    broad_category = DETECTOR_CLASSES[cls_id]
                else:
                    # Pretrained COCO: only keep class 4 (airplane)
                    if cls_id == 4:
                        broad_category = "unknown"
                    else:
                        continue  # Skip non-aircraft COCO detections

                # Stage 2: Classification
                crop = self._extract_crop(image, cx, cy, w, h)
                aircraft_type, cls_conf = self._classify_crop(crop)

                if aircraft_type is None:
                    aircraft_type = broad_category
                    cls_conf = None

                detections.append(DetectionResult(
                    aircraft_type=aircraft_type,
                    broad_category=broad_category,
                    confidence=det_conf,
                    classification_conf=cls_conf,
                    bbox_x=cx,
                    bbox_y=cy,
                    bbox_w=w,
                    bbox_h=h,
                ))

        return detections


detection_service = DetectionService()
