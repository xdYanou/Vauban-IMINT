"""
Convert MAR20 (Military Aircraft Recognition) dataset from Pascal VOC XML to YOLO format.

MAR20 has 20 US/NATO aircraft classes (A1-A20). For our use case (detecting aircraft
in satellite imagery regardless of nationality), we collapse them into broad categories
that transfer to Russian aircraft detection.

Mapping:
  fighter: A1(A-10), A6(F/A-18), A9(F-15), A12(F-16), A15(F-22)
  bomber: A2(B-1), A4(B-52), A8(B-2)
  transport: A5(C-130), A7(C-17), A13(C-5)
  tanker: A10(KC-10), A14(KC-135)
  surveillance: A3(P-3), A11(E-3), A17(U-2), A18(RQ-4), A20(E-8)
  rotary: A19(V-22)
  trainer: A16(T-38)
"""
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil
import random

# Source dataset
SRC = Path.home() / ".cache/kagglehub/datasets/khlaifiabilel/military-aircraft-recognition-dataset/versions/1"
# Output in YOLO format
OUT = Path(__file__).parent.parent / "datasets" / "mar20_yolo"

# Collapse 20 classes into broad categories for satellite detection
CLASS_MAP = {
    "A1": "fighter",
    "A2": "bomber",
    "A3": "surveillance",
    "A4": "bomber",
    "A5": "transport",
    "A6": "fighter",
    "A7": "transport",
    "A8": "bomber",
    "A9": "fighter",
    "A10": "tanker",
    "A11": "surveillance",
    "A12": "fighter",
    "A13": "transport",
    "A14": "tanker",
    "A15": "fighter",
    "A16": "trainer",
    "A17": "surveillance",
    "A18": "surveillance",
    "A19": "rotary",
    "A20": "surveillance",
}

CLASSES = ["fighter", "bomber", "transport", "tanker", "surveillance", "rotary", "trainer"]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}


def parse_voc_xml(xml_path: Path) -> list[dict]:
    """Parse Pascal VOC XML annotation."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    size = root.find("size")
    w = int(size.find("width").text)
    h = int(size.find("height").text)

    objects = []
    for obj in root.findall("object"):
        name = obj.find("name").text
        bbox = obj.find("bndbox")
        xmin = int(bbox.find("xmin").text)
        ymin = int(bbox.find("ymin").text)
        xmax = int(bbox.find("xmax").text)
        ymax = int(bbox.find("ymax").text)
        objects.append({
            "class": name,
            "xmin": xmin, "ymin": ymin,
            "xmax": xmax, "ymax": ymax,
            "img_w": w, "img_h": h,
        })
    return objects


def voc_to_yolo(obj: dict) -> str:
    """Convert VOC bbox to YOLO format (class_id cx cy w h) normalized."""
    mapped_class = CLASS_MAP.get(obj["class"])
    if mapped_class is None:
        return None

    class_id = CLASS_TO_ID[mapped_class]
    img_w, img_h = obj["img_w"], obj["img_h"]

    if img_w == 0 or img_h == 0:
        return None

    cx = ((obj["xmin"] + obj["xmax"]) / 2) / img_w
    cy = ((obj["ymin"] + obj["ymax"]) / 2) / img_h
    w = (obj["xmax"] - obj["xmin"]) / img_w
    h = (obj["ymax"] - obj["ymin"]) / img_h

    # Clamp values
    cx = max(0, min(1, cx))
    cy = max(0, min(1, cy))
    w = max(0, min(1, w))
    h = max(0, min(1, h))

    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def convert():
    xml_dir = SRC / "Annotations" / "Horizontal Bounding Boxes"
    img_dir = SRC / "JPEGImages"
    train_file = SRC / "ImageSets" / "Main" / "train.txt"
    test_file = SRC / "ImageSets" / "Main" / "test.txt"

    # Read splits
    train_ids = set(train_file.read_text().strip().split("\n"))
    test_ids = set(test_file.read_text().strip().split("\n"))

    # Split test into val and test (50/50)
    test_list = list(test_ids)
    random.seed(42)
    random.shuffle(test_list)
    mid = len(test_list) // 2
    val_ids = set(test_list[:mid])
    test_ids = set(test_list[mid:])

    splits = {"train": train_ids, "val": val_ids, "test": test_ids}
    stats = {s: {"images": 0, "objects": 0} for s in splits}
    class_counts = {c: 0 for c in CLASSES}

    for split_name, ids in splits.items():
        img_out = OUT / "images" / split_name
        lbl_out = OUT / "labels" / split_name
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_id in sorted(ids):
            xml_path = xml_dir / f"{img_id}.xml"
            img_path = img_dir / f"{img_id}.jpg"

            if not xml_path.exists() or not img_path.exists():
                continue

            objects = parse_voc_xml(xml_path)
            yolo_lines = []
            for obj in objects:
                line = voc_to_yolo(obj)
                if line:
                    yolo_lines.append(line)
                    mapped = CLASS_MAP[obj["class"]]
                    class_counts[mapped] += 1

            if not yolo_lines:
                continue

            # Copy image
            shutil.copy2(img_path, img_out / f"{img_id}.jpg")

            # Write YOLO label
            with open(lbl_out / f"{img_id}.txt", "w") as f:
                f.write("\n".join(yolo_lines) + "\n")

            stats[split_name]["images"] += 1
            stats[split_name]["objects"] += len(yolo_lines)

    # Write dataset YAML
    yaml_content = f"""path: {OUT}
train: images/train
val: images/val
test: images/test

names:
"""
    for i, c in enumerate(CLASSES):
        yaml_content += f"  {i}: {c}\n"

    with open(OUT / "data.yaml", "w") as f:
        f.write(yaml_content)

    # Print stats
    print("MAR20 -> YOLO conversion complete")
    print(f"Output: {OUT}")
    print()
    for split_name, s in stats.items():
        print(f"  {split_name}: {s['images']} images, {s['objects']} objects")
    print()
    print("Class distribution:")
    for c, count in class_counts.items():
        print(f"  {c}: {count}")


if __name__ == "__main__":
    convert()
