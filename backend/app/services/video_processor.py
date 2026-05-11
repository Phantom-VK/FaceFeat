import json
import sys
import uuid

import imageio.v3 as iio
import numpy as np
from mediapipe.tasks.python import vision
from sqlmodel import Session

from app.exceptions.exception import FaceFeatException
from app.logging.logger import logging
from app.models.video import Video, VideoFace
from app.services.face_detection import (
    detect_faces_in_frame,
    build_detector_options,
    build_landmarker_options,
    draw_faces,
)
from app.services.face_detection.config import (
    DETECTION_MODEL_PATH,
    LANDMARKER_MODEL_PATH,
    DETECTION_INTERVAL,
    NUM_FACES,
)

logger = logging.getLogger(__name__)


def _build_video_face_record(video_id: uuid.UUID, face_idx: int, frame_index: int, features: dict) -> VideoFace:
    """Map a face features dict to a VideoFace DB model."""
    return VideoFace(
        video_id=video_id,
        face_index=face_idx,
        frame_index=frame_index,
        confidence=features["confidence"],
        x=features["x"],
        y=features["y"],
        w=features["w"],
        h=features["h"],
        landmarks_json=json.dumps(features["landmarks"]),
        smile_score=features.get("smile_score"),
        blink_left=features.get("blink_left"),
        blink_right=features.get("blink_right"),
        brow_raise=features.get("brow_raise"),
        pitch=features.get("pitch"),
        yaw=features.get("yaw"),
        roll=features.get("roll"),
    )


def _update_video_record(session: Session, video_id: uuid.UUID, fps: int, frame_count: int, output_path: str):
    """Persist final video metadata to DB."""
    video = session.get(Video, video_id)
    video.fps = fps
    video.frame_count = frame_count
    video.processed_path = output_path
    session.add(video)


def process_video(video_id: uuid.UUID, input_path: str, output_path: str, session: Session):
    try:
        logger.info(f"Starting video processing for video_id={video_id}")

        meta = iio.immeta(input_path, plugin="pyav")
        fps = int(round(float(meta.get("fps", 30))))
        logger.info(f"Video FPS: {fps}")

        detector_options = build_detector_options(DETECTION_MODEL_PATH)
        landmarker_options = build_landmarker_options(LANDMARKER_MODEL_PATH, NUM_FACES)

        frame_index = 0
        roi_records = []

        with vision.FaceDetector.create_from_options(detector_options) as detector, \
             vision.FaceLandmarker.create_from_options(landmarker_options) as landmarker, \
             iio.imopen(output_path, "w", plugin="pyav") as writer:

            writer.init_video_stream("h264", fps=fps)

            for frame in iio.imiter(input_path, plugin="pyav"):
                frame_rgb = np.ascontiguousarray(frame[..., :3].astype(np.uint8))
                timestamp_ms = int((frame_index * 1000) / fps)
                faces_for_frame = []

                if frame_index % DETECTION_INTERVAL == 0:
                    faces_for_frame = detect_faces_in_frame(detector, landmarker, frame_rgb, timestamp_ms)

                    for face_idx, features in enumerate(faces_for_frame):
                        roi_records.append(_build_video_face_record(video_id, face_idx, frame_index, features))

                    logger.info(f"Detected | frame={frame_index} | faces={len(faces_for_frame)}")

                processed_frame = draw_faces(frame_rgb, faces_for_frame) if faces_for_frame else frame_rgb
                writer.write_frame(processed_frame)

                if frame_index % 60 == 0:
                    logger.info(f"Processed frame={frame_index}")

                frame_index += 1

        _update_video_record(session, video_id, fps, frame_index, str(output_path))
        for record in roi_records:
            session.add(record)
        session.commit()
        logger.info(f"DB updated for video_id={video_id}")

    except Exception as e:
        session.rollback()
        raise FaceFeatException(str(e), sys)