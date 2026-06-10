from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    thumbnail = Column(String(500), nullable=True)
    has_cta = Column(Boolean, default=False)
    has_logo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    episodes = relationship("Episode", back_populates="show", cascade="all, delete-orphan")
    promos = relationship("Promo", back_populates="show", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=False)
    title = Column(String(255), nullable=False)
    filename = Column(String(500), nullable=False)
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    show = relationship("Show", back_populates="episodes")


class Promo(Base):
    __tablename__ = "promos"

    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=False)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    ad_type = Column(String(50), nullable=False)  # ep-cut, trailer
    duration = Column(Float, nullable=True)
    aspect_ratio = Column(String(10), default="9:16")
    mode = Column(String(50), default="review_first")  # review_first, full_auto
    status = Column(String(50), default="processing")  # processing, ready, failed
    output_path = Column(String(500), nullable=True)
    thumbnail = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    show = relationship("Show", back_populates="promos")
    episode = relationship("Episode")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
