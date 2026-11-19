"""
Prepare the 114-class aircraft crop dataset for Stage 2 classification.

The dataset has pre-cropped aircraft images in crop/<ClassName>/ folders.
We filter to Russian/relevant types and organize for PyTorch ImageFolder format.

Russian types we care about (present at monitored airbases):
  Su-24, Su-25, Su-34, Su-57, MiG-29, MiG-31,
  Tu-95, Tu-160, Tu-22M, Il-76,
  Ka-52, Ka-27, Mi-8, Mi-24, Mi-26, Mi-28,
  An-124, An-22

We also keep some NATO types that might appear in OSINT or for model robustness.
"""
from pathlib import Path
import shutil
import random

SRC = Path.home() / ".cache/kagglehub/datasets/a2015003713/militaryaircraftdetectiondataset/versions/105/crop"
OUT = Path(__file__).parent.parent / "datasets" / "aircraft_classifier"

# Russian and key aircraft types to keep for classification
# These are the types likely to be seen on Russian airbases
RUSSIAN_TYPES = [
    "Su24", "Su25", "Su34", "Su47", "Su57",
    "Mig29", "Mig31",
    "Tu95", "Tu160", "Tu22M",
    "Il76",
    "Ka52", "Ka27",
    "Mi8", "Mi24", "Mi26", "Mi28",
    "An124", "An22",
    "H6",  # Chinese but relevant
]

# Additional types for robustness (NATO equivalents the model should distinguish)
NATO_TYPES = [
    "F15", "F16", "F18", "F22", "F35",
    "B1", "B2", "B52",
    "C130", "C17", "C5",
    "A10", "AH64",
    "KC135",
    "E2",
]

KEEP_TYPES = RUSSIAN_TYPES + NATO_TYPES


def prepare():
    random.seed(42)

    if not SRC.exists():
        print(f"Source not found: {SRC}")
        return

    available = [d.name for d in SRC.iterdir() if d.is_dir()]
    print(f"Available classes: {len(available)}")

    keep = [t for t in KEEP_TYPES if t in available]
    missing = [t for t in KEEP_TYPES if t not in available]
    if missing:
        print(f"Missing classes (skipped): {missing}")

    print(f"Keeping {len(keep)} classes")

    total_stats = {}

    for cls_name in keep:
        cls_dir = SRC / cls_name
        images = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.png")) + list(cls_dir.glob("*.jpeg"))

        if len(images) < 5:
            print(f"  Skipping {cls_name}: only {len(images)} images")
            continue

        random.shuffle(images)

        # 70/15/15 split
        n = len(images)
        n_train = int(n * 0.7)
        n_val = int(n * 0.15)

        splits = {
            "train": images[:n_train],
            "val": images[n_train:n_train + n_val],
            "test": images[n_train + n_val:],
        }

        total_stats[cls_name] = {}

        for split_name, split_images in splits.items():
            out_dir = OUT / split_name / cls_name
            out_dir.mkdir(parents=True, exist_ok=True)

            for img in split_images:
                shutil.copy2(img, out_dir / img.name)

            total_stats[cls_name][split_name] = len(split_images)

    # Print summary
    print("\nDataset prepared for classification:")
    print(f"Output: {OUT}\n")
    print(f"{'Class':<12} {'Train':>6} {'Val':>6} {'Test':>6} {'Total':>6}")
    print("-" * 42)
    for cls_name, counts in sorted(total_stats.items()):
        t, v, te = counts.get("train", 0), counts.get("val", 0), counts.get("test", 0)
        print(f"{cls_name:<12} {t:>6} {v:>6} {te:>6} {t+v+te:>6}")

    total_t = sum(c.get("train", 0) for c in total_stats.values())
    total_v = sum(c.get("val", 0) for c in total_stats.values())
    total_te = sum(c.get("test", 0) for c in total_stats.values())
    print("-" * 42)
    print(f"{'TOTAL':<12} {total_t:>6} {total_v:>6} {total_te:>6} {total_t+total_v+total_te:>6}")


if __name__ == "__main__":
    prepare()
