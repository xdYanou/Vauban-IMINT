"""
Aircraft detection with base-context classification and country-level filtering.

Stage 1: YOLOv8 detects aircraft and gives a raw classification.
Stage 2: Intelligent filtering:
  - Base-specific override: maps shape categories to known stationed types
  - Country-level filtering: removes impossible detections (no Su-35 at US bases)
  - Keeps raw output only for bases with no context
"""
import json
import logging
from pathlib import Path
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("vauban.detection")

# Map model output types to shape categories
SHAPE_CATEGORY = {
    "Su-35": "fighter", "F-15": "fighter", "F-16": "fighter",
    "F-22": "fighter", "FA-18": "fighter",
    "B-52": "heavy_bomber", "B-1B": "swing_bomber", "Tu-95": "heavy_bomber",
    "Tu-160": "swing_bomber", "Tu-22M": "medium_bomber",
    "Su-34": "strike", "Su-24": "strike",
    "C-130": "medium_transport", "C-17": "heavy_transport", "C-5": "heavy_transport",
    "KC-135": "tanker", "KC-10": "tanker",
    "E-3": "awacs", "E-8": "awacs", "P-3C": "patrol",
    "aircraft": "unknown",
}

# Which raw model types are plausible for each country
# If a detection type isn't in the country's allowed list, it gets remapped via shape
COUNTRY_PLAUSIBLE_TYPES = {
    # NATO / Western — only US/NATO types are plausible raw detections
    "USA": {"F-15", "F-16", "F-22", "FA-18", "B-52", "B-1B", "C-130", "C-17", "C-5", "KC-135", "KC-10", "E-3", "E-8", "P-3C"},
    "UK": {"F-15", "F-16", "F-22", "FA-18", "C-130", "C-17", "KC-135", "E-3", "P-3C"},
    "Germany": {"F-16", "FA-18", "C-130", "C-17", "E-3"},
    "France": {"FA-18", "C-130", "C-17", "KC-135", "E-3"},
    "Italy": {"F-16", "FA-18", "C-130", "E-3"},
    "NATO": {"F-15", "F-16", "F-22", "FA-18", "B-52", "B-1B", "C-130", "C-17", "C-5", "KC-135", "KC-10", "E-3", "E-8", "P-3C"},
    "Canada": {"FA-18", "C-130", "C-17"},
    "Australia": {"FA-18", "F-16", "C-130", "C-17", "E-3", "P-3C", "KC-135"},
    "Japan": {"F-15", "F-16", "C-130", "E-3", "P-3C", "KC-135"},
    "South Korea": {"F-16", "F-15", "C-130", "E-3"},
    "Norway": {"F-16", "C-130", "P-3C"},
    "Netherlands": {"F-16", "C-130"},
    "Belgium": {"F-16", "C-130"},
    "Poland": {"F-16", "C-130"},
    "Spain": {"FA-18", "C-130"},
    "Portugal": {"F-16", "C-130"},
    "Turkey": {"F-16", "C-130", "KC-135", "E-3"},
    "Czech Republic": {"F-16", "C-130"},
    "Romania": {"F-16", "C-130"},
    "Bulgaria": {"F-16", "C-130"},

    # Russia — only Russian types
    "Russia": {"Su-35", "Su-34", "Su-24", "Tu-95", "Tu-160", "Tu-22M"},

    # Iran — mix of Russian and old US
    "Iran": {"F-16", "F-15", "FA-18", "Su-24", "C-130"},

    # Israel — US types
    "Israel": {"F-15", "F-16", "F-22", "C-130", "KC-135", "E-3"},

    # China — mapped via base context, but shape-wise similar to Russian
    "China": {"Su-35", "Su-34", "Su-24"},

    # Taiwan — US types
    "Taiwan": {"F-16", "FA-18", "C-130", "E-3"},

    # India — mix
    "India": {"Su-35", "Su-34", "C-130", "C-17"},

    # Pakistan — US + Chinese shapes
    "Pakistan": {"F-16", "C-130"},

    # Middle East
    "Saudi Arabia": {"F-15", "F-16", "FA-18", "C-130", "E-3", "KC-135", "B-52"},
    "UAE": {"F-16", "FA-18", "C-130", "C-17", "E-3"},
    "Egypt": {"F-16", "FA-18", "C-130", "Su-35"},
    "Jordan": {"F-16", "F-15", "C-130"},

    # South America
    "Brazil": {"F-16", "C-130"},
    "Argentina": {"C-130"},
    "Mexico": {"C-130"},
}

# Country-level shape defaults (when a detection is filtered out, remap to this)
COUNTRY_SHAPE_DEFAULTS = {
    "USA": {"fighter": "F-15", "strike": "F-15E", "heavy_bomber": "B-52", "swing_bomber": "B-1B", "medium_bomber": "B-1B", "medium_transport": "C-130", "heavy_transport": "C-17", "tanker": "KC-135", "awacs": "E-3", "patrol": "P-3C"},
    "UK": {"fighter": "Typhoon", "strike": "Typhoon", "medium_transport": "C-130J", "heavy_transport": "C-17", "tanker": "Voyager", "awacs": "E-7 Wedgetail", "patrol": "P-8A Poseidon"},
    "Germany": {"fighter": "Eurofighter", "strike": "Tornado", "medium_transport": "C-130J", "heavy_transport": "A400M", "awacs": "E-3"},
    "France": {"fighter": "Rafale", "strike": "Rafale", "medium_transport": "C-130J", "heavy_transport": "A400M", "tanker": "A330 MRTT", "awacs": "E-3F", "patrol": "ATL2"},
    "Italy": {"fighter": "Eurofighter", "strike": "Tornado", "medium_transport": "C-130J", "heavy_transport": "C-17"},
    "Spain": {"fighter": "EF-18", "strike": "EF-18", "medium_transport": "C-130"},
    "Norway": {"fighter": "F-35A", "medium_transport": "C-130J", "patrol": "P-8A"},
    "Netherlands": {"fighter": "F-35A", "medium_transport": "C-130"},
    "Belgium": {"fighter": "F-16AM", "medium_transport": "C-130"},
    "Poland": {"fighter": "F-16C", "medium_transport": "C-130E"},
    "Turkey": {"fighter": "F-16C", "medium_transport": "C-130", "tanker": "KC-135", "awacs": "E-7"},
    "Israel": {"fighter": "F-35I Adir", "strike": "F-15I Ra'am", "medium_transport": "C-130J", "tanker": "Boeing 707", "awacs": "G550 CAEW"},
    "Japan": {"fighter": "F-35A", "strike": "F-2A", "medium_transport": "C-130", "heavy_transport": "C-2", "awacs": "E-767", "patrol": "P-1"},
    "South Korea": {"fighter": "KF-21", "strike": "F-15K", "medium_transport": "C-130", "awacs": "E-737"},
    "Taiwan": {"fighter": "F-16V", "strike": "Mirage 2000-5", "medium_transport": "C-130", "awacs": "E-2K"},
    "Saudi Arabia": {"fighter": "F-15SA", "strike": "Typhoon", "medium_transport": "C-130", "awacs": "E-3A", "tanker": "KC-130"},
    "UAE": {"fighter": "F-16E Block 60", "strike": "Mirage 2000-9", "medium_transport": "C-130", "heavy_transport": "C-17"},
    "Egypt": {"fighter": "Rafale DM", "strike": "MiG-29M2", "medium_transport": "C-130", "heavy_transport": "C-17"},
    "Jordan": {"fighter": "F-16AM", "strike": "F-16AM", "medium_transport": "C-130"},
    "India": {"fighter": "Rafale", "strike": "Su-30MKI", "medium_transport": "C-130J", "heavy_transport": "C-17", "awacs": "A-50EI", "tanker": "Il-78"},
    "Pakistan": {"fighter": "JF-17", "strike": "F-16C Block 52", "medium_transport": "C-130"},
    "China": {"fighter": "J-20", "strike": "J-16", "heavy_bomber": "H-6K", "medium_transport": "Y-9", "heavy_transport": "Y-20", "awacs": "KJ-500"},
    "Brazil": {"fighter": "Gripen E", "medium_transport": "C-130"},
    "Canada": {"fighter": "CF-18", "medium_transport": "CC-130J", "heavy_transport": "CC-177"},
    "Australia": {"fighter": "F-35A", "strike": "F/A-18F", "medium_transport": "C-130J", "heavy_transport": "C-17", "tanker": "KC-30A", "patrol": "P-8A"},
}

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


def reclassify_for_base(detections: list, airbase_name: str, country: str = "", known_units: str = "") -> list:
    """
    Intelligent reclassification:
    1. If base has specific context in base_context.json → use that
    2. Else if country has defaults → filter implausible types, remap via shape
    3. Else → return raw detections
    """
    ctx = _load_base_context()
    base_map = ctx.get(airbase_name, {})

    reclassified = []
    for det in detections:
        shape = SHAPE_CATEGORY.get(det.aircraft_type, "unknown")

        # Priority 1: Base-specific mapping
        if base_map and shape in base_map:
            reclassified.append(DetectionResult(
                aircraft_type=base_map[shape],
                confidence=det.confidence,
                bbox_x=det.bbox_x, bbox_y=det.bbox_y,
                bbox_w=det.bbox_w, bbox_h=det.bbox_h,
            ))
            continue

        # Priority 2: Country-level filtering
        plausible = COUNTRY_PLAUSIBLE_TYPES.get(country)
        country_defaults = COUNTRY_SHAPE_DEFAULTS.get(country)

        if plausible is not None:
            if det.aircraft_type in plausible:
                # Raw type is plausible for this country — keep it
                reclassified.append(det)
            elif country_defaults and shape in country_defaults:
                # Implausible type — remap to country default for this shape
                reclassified.append(DetectionResult(
                    aircraft_type=country_defaults[shape],
                    confidence=det.confidence,
                    bbox_x=det.bbox_x, bbox_y=det.bbox_y,
                    bbox_w=det.bbox_w, bbox_h=det.bbox_h,
                ))
            else:
                # No mapping available — keep raw but it's likely wrong
                reclassified.append(det)
        else:
            # No country info — keep raw
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
        from ultralytics import YOLO
        model_dir = Path(settings.model_storage_path)
        for name in ["vauban_detect_v3.pt", "vauban_detect_v2.pt", "vauban_detect_v1.pt"]:
            path = model_dir / name
            if path.exists():
                self.model = YOLO(str(path))
                logger.info(f"Loaded model: {path}")
                return
        self.model = YOLO("yolov8n.pt")
        logger.info("No trained model found — using pretrained COCO fallback")

    def detect(self, image_path: str, airbase_name: str = None, country: str = None, known_units: str = None) -> list[DetectionResult]:
        if self.model is None:
            self.load_model()

        results = self.model(image_path, conf=settings.detection_confidence_threshold, imgsz=1280, augment=True)
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
                    bbox_x=cx, bbox_y=cy, bbox_w=w, bbox_h=h,
                ))

        # Apply intelligent reclassification
        if airbase_name:
            detections = reclassify_for_base(detections, airbase_name, country or "", known_units or "")

        return detections


detection_service = DetectionService()
