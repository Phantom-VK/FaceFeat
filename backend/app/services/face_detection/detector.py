import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision

from app.services.face_detection.config import CROP_PADDING
from app.services.face_detection.landmarker import run_landmarker_on_crop
from app.services.face_detection.utils import safe_float


def build_detector_options(model_path: str) -> vision.FaceDetectorOptions:
    """Build FaceDetector options for VIDEO running mode."""
    return vision.FaceDetectorOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.VIDEO,
        min_detection_confidence=0.4,
    )


def _bbox_fallback(bbox, confidence: float) -> dict:
    """Return a bbox-only face dict when landmarker returns no result."""
    return {
        "x": int(bbox.origin_x),
        "y": int(bbox.origin_y),
        "w": int(bbox.width),
        "h": int(bbox.height),
        "confidence": confidence,
        "landmarks": [],
        "smile_score": None,
        "blink_left": None,
        "blink_right": None,
        "brow_raise": None,
        "pitch": None,
        "yaw": None,
        "roll": None,
    }


def detect_faces_in_frame(
    detector,
    landmarker,
    frame_rgb: np.ndarray,
    timestamp_ms: int,
) -> list[dict]:
    """Run full two-stage detection on one frame. Returns list of face feature dicts."""
    frame_h, frame_w = frame_rgb.shape[:2]

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    detections = sorted(list(detection_result.detections or []), key=lambda d: d.bounding_box.origin_x)
    faces = []

    for detection in detections:
        bbox = detection.bounding_box
        confidence = safe_float(detection.categories[0].score if detection.categories else 0.0)

        x1 = max(0, int(bbox.origin_x) - CROP_PADDING)
        y1 = max(0, int(bbox.origin_y) - CROP_PADDING)
        x2 = min(frame_w, int(bbox.origin_x + bbox.width) + CROP_PADDING)
        y2 = min(frame_h, int(bbox.origin_y + bbox.height) + CROP_PADDING)

        crop_rgb = frame_rgb[y1:y2, x1:x2]
        features = run_landmarker_on_crop(landmarker, crop_rgb, x1, y1, frame_w, frame_h)

        if features is None:
            features = _bbox_fallback(bbox, confidence)
        else:
            features["confidence"] = confidence

        faces.append(features)

    return faces