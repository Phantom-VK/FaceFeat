import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Row
from sqlmodel import Session, select

from app.core.database import get_session
from app.logging.logger import logging
from app.models.video import Video, VideoFace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["roi"])



def _serialize_face(face: VideoFace, include_landmarks: bool) -> dict:
    """Serialize a VideoFace record to a response dict."""
    data = {
        "frame_index":  face.frame_index,
        "face_index":   face.face_index,
        "confidence":   face.confidence,
        "bbox": {
            "x": face.x,
            "y": face.y,
            "w": face.w,
            "h": face.h,
        },
        "expressions": {
            "smile_score": face.smile_score,
            "blink_left":  face.blink_left,
            "blink_right": face.blink_right,
            "brow_raise":  face.brow_raise,
        },
        "pose": {
            "pitch": face.pitch,
            "yaw":   face.yaw,
            "roll":  face.roll,
        },
    }
    if include_landmarks:
        import json
        data["landmarks"] = json.loads(face.landmarks_json) if face.landmarks_json else []
    return data


def _aggregate_faces(faces: list[VideoFace]) -> list[dict]:
    """Aggregate per-frame records into per-face summaries."""
    from collections import defaultdict

    buckets: dict[int, list[VideoFace]] = defaultdict(list)
    for face in faces:
        buckets[face.face_index].append(face)

    summaries = []
    for face_index, records in sorted(buckets.items()):
        def avg(values):
            valid = [v for v in values if v is not None]
            return round(sum(valid) / len(valid), 4) if valid else None

        summaries.append({
            "face_index":      face_index,
            "frames_detected": len(records),
            "avg_confidence":  avg([r.confidence  for r in records]),
            "avg_smile":       avg([r.smile_score for r in records]),
            "avg_blink_left":  avg([r.blink_left  for r in records]),
            "avg_blink_right": avg([r.blink_right for r in records]),
            "avg_brow_raise":  avg([r.brow_raise  for r in records]),
            "avg_pitch":       avg([r.pitch for r in records]),
            "avg_yaw":         avg([r.yaw   for r in records]),
            "avg_roll":        avg([r.roll  for r in records]),
        })

    return summaries



def _get_video_or_404(video_id: uuid.UUID, session: Session) -> Video:
    """Fetch video or raise 404."""
    video = session.get(Video, video_id)
    if not video:
        logger.warning(f"Video not found | video_id={video_id}")
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found.")
    return video


def _fetch_faces(
    video_id: uuid.UUID,
    session: Session,
    skip: int,
    limit: int,
) -> list[Row[Any]]:
    """Query VideoFace records for a video with pagination."""
    statement = (
        select(VideoFace)
        .where(VideoFace.video_id == video_id)
        .order_by(VideoFace.frame_index, VideoFace.face_index)
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())



@router.get("/{video_id}/roi")
def get_roi(
    video_id: uuid.UUID,
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    landmarks: bool = Query(default=False, description="Include 478 landmarks per face"),
    session: Session = Depends(get_session),
):
    """
    Return per-frame face ROI data and per-face aggregated summary for a video.

    - **skip / limit** — paginate through raw frame records
    - **landmarks** — set to true to include 478-point landmark arrays (large payload)
    """
    logger.info(
        f"ROI request | video_id={video_id} | "
        f"skip={skip} limit={limit} landmarks={landmarks}"
    )

    try:
        video = _get_video_or_404(video_id, session)

        # Fetch paginated raw records
        faces = _fetch_faces(video_id, session, skip, limit)

        if not faces:
            logger.info(f"No ROI records found | video_id={video_id}")
            return {
                "video_id":   str(video_id),
                "total":      0,
                "skip":       skip,
                "limit":      limit,
                "summary":    [],
                "frames":     [],
            }

        # Fetch ALL records (unpaginated) for accurate aggregation
        all_faces = _fetch_faces(video_id, session, skip=0, limit=100_000)

        raw_frames  = [_serialize_face(f, include_landmarks=landmarks) for f in faces]
        aggregation = _aggregate_faces(all_faces)

        logger.info(
            f"ROI response | video_id={video_id} | "
            f"frames={len(raw_frames)} | faces={len(aggregation)}"
        )

        return {
            "video_id": str(video_id),
            "total":    len(all_faces),
            "skip":     skip,
            "limit":    limit,
            "summary":  aggregation,
            "frames":   raw_frames,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ROI | video_id={video_id} | error={e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching ROI data.")