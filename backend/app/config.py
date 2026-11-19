from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Vauban"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./vauban.db"

    # Copernicus Data Space (Sentinel Hub)
    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""

    # Storage
    image_storage_path: str = str(Path(__file__).parent.parent / "storage" / "images")
    model_storage_path: str = str(Path(__file__).parent.parent / "ml" / "models")

    # Detection
    detection_confidence_threshold: float = 0.5
    detection_model_name: str = "yolov8n.pt"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
