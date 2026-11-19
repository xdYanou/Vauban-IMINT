from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.models.database import Base


class Airbase(Base):
    __tablename__ = "airbases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    icao_code = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    country = Column(String, default="Russia")
    region = Column(String, nullable=True)
    military_district = Column(String, nullable=True)
    known_units = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    observations = relationship("Observation", back_populates="airbase")
    capture_zones = relationship("CaptureZone", back_populates="airbase", cascade="all, delete-orphan")


class CaptureZone(Base):
    """A rectangular capture area for an airbase. Each base can have multiple zones."""
    __tablename__ = "capture_zones"

    id = Column(Integer, primary_key=True, index=True)
    airbase_id = Column(Integer, ForeignKey("airbases.id"), nullable=False)
    label = Column(String, nullable=True)  # e.g. "main-apron", "north-shelters"
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    zoom = Column(Integer, default=17)
    grid_size = Column(Integer, default=6)  # tiles per side
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    airbase = relationship("Airbase", back_populates="capture_zones")


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    airbase_id = Column(Integer, ForeignKey("airbases.id"), nullable=False)
    observation_date = Column(DateTime, nullable=False)
    image_path = Column(String, nullable=False)
    source = Column(String, default="sentinel-2")
    cloud_cover_pct = Column(Float, nullable=True)
    zone_id = Column(Integer, ForeignKey("capture_zones.id"), nullable=True)
    zone_label = Column(String, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    airbase = relationship("Airbase", back_populates="observations")
    detections = relationship("Detection", back_populates="observation")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    observation_id = Column(Integer, ForeignKey("observations.id"), nullable=False)
    aircraft_type = Column(String, nullable=False)
    broad_category = Column(String, nullable=True)
    confidence = Column(Float, nullable=False)
    classification_conf = Column(Float, nullable=True)
    bbox_x = Column(Float, nullable=False)
    bbox_y = Column(Float, nullable=False)
    bbox_w = Column(Float, nullable=False)
    bbox_h = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    observation = relationship("Observation", back_populates="detections")
