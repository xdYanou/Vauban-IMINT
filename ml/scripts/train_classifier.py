"""
Stage 2: Fine-grained aircraft type classifier.

Takes cropped aircraft patches (from Stage 1 YOLO detections) and classifies
into specific types (Su-34, Tu-95, MiG-31, etc.).

Uses EfficientNet-B0 with transfer learning from ImageNet.

Usage:
    # First prepare the dataset
    python prepare_classifier.py

    # Then train
    python train_classifier.py --data ../datasets/aircraft_classifier --epochs 50
"""
import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models


def get_transforms(train=True):
    if train:
        return transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(180),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


def train(data_dir: str, epochs: int = 50, batch: int = 32, lr: float = 0.001):
    data_path = Path(data_dir)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Datasets
    train_ds = datasets.ImageFolder(data_path / "train", transform=get_transforms(train=True))
    val_ds = datasets.ImageFolder(data_path / "val", transform=get_transforms(train=False))

    num_classes = len(train_ds.classes)
    print(f"Classes ({num_classes}): {train_ds.classes}")
    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=batch, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_ds, batch_size=batch, shuffle=False, num_workers=4)

    # Model: EfficientNet-B0 with custom head
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    model = model.to(device)

    # Freeze backbone initially
    for param in model.features.parameters():
        param.requires_grad = False

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.classifier.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    best_val_acc = 0.0
    output_dir = Path(__file__).parent.parent / "models"
    output_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(epochs):
        # Unfreeze backbone after 10 epochs for fine-tuning
        if epoch == 10:
            print("Unfreezing backbone for fine-tuning")
            for param in model.features.parameters():
                param.requires_grad = True
            optimizer = torch.optim.Adam(model.parameters(), lr=lr * 0.1)
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

        # Train
        model.train()
        train_loss, train_correct, train_total = 0, 0, 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)
            train_correct += (outputs.argmax(1) == labels).sum().item()
            train_total += images.size(0)

        # Validate
        model.eval()
        val_loss, val_correct, val_total = 0, 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                val_correct += (outputs.argmax(1) == labels).sum().item()
                val_total += images.size(0)

        train_acc = train_correct / train_total
        val_acc = val_correct / val_total
        avg_val_loss = val_loss / val_total
        scheduler.step(avg_val_loss)

        print(f"Epoch {epoch+1}/{epochs} | "
              f"Train Loss: {train_loss/train_total:.4f} Acc: {train_acc:.4f} | "
              f"Val Loss: {avg_val_loss:.4f} Acc: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_path = output_dir / "vauban_classifier_v1.pt"
            torch.save({
                "model_state_dict": model.state_dict(),
                "classes": train_ds.classes,
                "num_classes": num_classes,
                "best_val_acc": best_val_acc,
                "epoch": epoch,
            }, save_path)
            print(f"  Saved best model (val_acc={val_acc:.4f})")

    print(f"\nTraining complete. Best val accuracy: {best_val_acc:.4f}")
    print(f"Model saved to {output_dir / 'vauban_classifier_v1.pt'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Vauban Stage 2: Aircraft Classifier")
    parser.add_argument("--data", type=str, required=True, help="Path to classifier dataset")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.001)
    args = parser.parse_args()

    train(args.data, args.epochs, args.batch, args.lr)
