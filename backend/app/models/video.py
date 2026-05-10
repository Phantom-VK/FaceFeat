import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, ForeignKey
from sqlmodel import SQLModel, Field, Relationship

from app.logging.logger import logging

logger = logging.getLogger(__name__)


class VideoBase(SQLModel):
    """Fields shared between DB and API."""
    fps: int = Field(description="Frames per second")
    frame_count: int = Field(description="Total number of frames")
    original_path: str = Field(description="Path to original uploaded video")
    processed_path: str = Field(description="Path to processed video with ROI")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Video(VideoBase, table=True):
    """Video table."""
    __tablename__ = "videos"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    faces: list["VideoFace"] = Relationship(back_populates="video")


class VideoFaceBase(SQLModel):
    """Per-frame ROI + embedding."""
    frame_index: int = Field(description="Frame number within video")
    confidence: Optional[float] = Field(default=None, description="Detector confidence")

    x: Optional[int] = Field(default=None, description="ROI x coordinate (left)")
    y: Optional[int] = Field(default=None, description="ROI y coordinate (top)")
    w: Optional[int] = Field(default=None, description="ROI width")
    h: Optional[int] = Field(default=None, description="ROI height")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VideoFace(VideoFaceBase, table=True):
    """Face/ROI per frame."""
    __tablename__ = "video_faces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    video_id: uuid.UUID = Field(
        sa_column=Column(
            "video_id",
            ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )

    video: Optional[Video] = Relationship(back_populates="faces")