"""
Stage 1: Fine-tune YOLOv8 on MAR20 satellite imagery for aircraft detection.

Detects aircraft in overhead/satellite imagery and classifies into broad categories:
  fighter, bomber, transport, tanker, surveillance, rotary, trainer

Usage:
    # First prepare the dataset
    python prepare_mar20.py

    # Then train
    python train.py --data ../datasets/mar20_yolo/data.yaml --epochs 100
"""
import argparse
from pathlib import Path
from ultralytics import YOLO


def train(data_yaml: str, epochs: int = 100, batch: int = 16, imgsz: int = 640, base_model: str = "yolov8n.pt"):
    model = YOLO(base_model)

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        project=str(Path(__file__).parent.parent / "runs" / "detection"),
        name="vauban_detect_v1",
        # Transfer learning: freeze backbone initially
        freeze=10,
        lr0=0.001,
        lrf=0.01,
        # Augmentation tuned for satellite imagery
        hsv_h=0.015,
        hsv_s=0.4,
        hsv_v=0.3,
        degrees=180.0,  # Aircraft can face any direction
        translate=0.1,
        scale=0.5,
        flipud=0.5,
        fliplr=0.5,
        mosaic=1.0,
    )

    # Copy best model to models/
    best_path = Path(__file__).parent.parent / "runs" / "detection" / "vauban_detect_v1" / "weights" / "best.pt"
    if best_path.exists():
        import shutil
        output = Path(__file__).parent.parent / "models" / "vauban_detect_v1.pt"
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(best_path, output)
        print(f"Best model saved to {output}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Vauban Stage 1: Aircraft Detection")
    parser.add_argument("--data", type=str, required=True, help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--base-model", type=str, default="yolov8n.pt")
    args = parser.parse_args()

    train(args.data, args.epochs, args.batch, args.imgsz, args.base_model)
