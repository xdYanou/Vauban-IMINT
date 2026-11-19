from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
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


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    airbase_id = Column(Integer, ForeignKey("airbases.id"), nullable=False)
    observation_date = Column(DateTime, nullable=False)
    image_path = Column(String, nullable=False)
    source = Column(String, default="sentinel-2")
    cloud_cover_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    airbase = relationship("Airbase", back_populates="observations")
    detections = relationship("Detection", back_populates="observation")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    observation_id = Column(Integer, ForeignKey("observations.id"), nullable=False)
    aircraft_type = Column(String, nullable=False)      # Fine-grained (e.g. "Su-34") or broad category
    broad_category = Column(String, nullable=True)       # Stage 1 broad category (e.g. "fighter")
    confidence = Column(Float, nullable=False)           # Stage 1 detection confidence
    classification_conf = Column(Float, nullable=True)   # Stage 2 classification confidence
    bbox_x = Column(Float, nullable=False)
    bbox_y = Column(Float, nullable=False)
    bbox_w = Column(Float, nullable=False)
    bbox_h = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    observation = relationship("Observation", back_populates="detections")
