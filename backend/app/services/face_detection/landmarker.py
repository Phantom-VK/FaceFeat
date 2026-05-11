import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision

from app.services.face_detection.utils import safe_float, pose_from_matrix


def build_landmarker_options(model_path: str, num_faces: int) -> vision.FaceLandmarkerOptions:
    """Build FaceLandmarker options for IMAGE running mode."""
    return vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=num_faces,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        min_face_detection_confidence=0.4,
        min_face_presence_confidence=0.4,
        min_tracking_confidence=0.4,
    )


def _extract_landmarks(landmarks_raw, crop_rgb, x_offset, y_offset, frame_w, frame_h):
    """Convert normalized crop landmarks to absolute frame pixel coordinates."""
    crop_h, crop_w = crop_rgb.shape[:2]
    abs_landmarks = []
    xs, ys = [], []

    for lm in landmarks_raw:
        abs_x = max(0.0, min(float(frame_w - 1), x_offset + float(lm.x) * crop_w))
        abs_y = max(0.0, min(float(frame_h - 1), y_offset + float(lm.y) * crop_h))
        xs.append(abs_x)
        ys.append(abs_y)
        abs_landmarks.append({"x": abs_x, "y": abs_y, "z": float(lm.z)})

    return abs_landmarks, xs, ys


def _extract_blendshapes(blendshapes_raw) -> dict:
    """Flatten blendshape list into a name→score dict."""
    blend = {}
    for item in blendshapes_raw:
        if item.category_name:
            blend[item.category_name] = safe_float(item.score)
    return blend


def _build_face_features(abs_landmarks, xs, ys, blend, result, frame_w, frame_h, x_offset, y_offset, crop_w, crop_h):
    """Assemble final face features dict from landmarks, blendshapes, and head pose."""
    smile_score = (blend.get("mouthSmileLeft", 0.0) + blend.get("mouthSmileRight", 0.0)) / 2.0

    pitch = yaw = roll = None
    if result.facial_transformation_matrixes:
        pitch, yaw, roll = pose_from_matrix(result.facial_transformation_matrixes[0].data)

    x1 = int(max(0, min(xs))) if xs else x_offset
    y1 = int(max(0, min(ys))) if ys else y_offset
    x2 = int(min(frame_w, max(xs))) if xs else (x_offset + crop_w)
    y2 = int(min(frame_h, max(ys))) if ys else (y_offset + crop_h)

    return {
        "x": x1,
        "y": y1,
        "w": max(1, x2 - x1),
        "h": max(1, y2 - y1),
        "confidence": 1.0,
        "landmarks": abs_landmarks,
        "smile_score": smile_score,
        "blink_left": blend.get("eyeBlinkLeft"),
        "blink_right": blend.get("eyeBlinkRight"),
        "brow_raise": blend.get("browInnerUp"),
        "pitch": pitch,
        "yaw": yaw,
        "roll": roll,
    }


def run_landmarker_on_crop(
    landmarker,
    crop_rgb: np.ndarray,
    x_offset: int,
    y_offset: int,
    frame_w: int,
    frame_h: int,
) -> dict | None:
    """Run FaceLandmarker on a cropped face region and return absolute frame features."""
    if crop_rgb.size == 0:
        return None

    crop_rgb = np.ascontiguousarray(crop_rgb.astype(np.uint8))
    crop_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=crop_rgb)
    result = landmarker.detect(crop_image)

    if not result.face_landmarks:
        return None

    crop_h, crop_w = crop_rgb.shape[:2]
    abs_landmarks, xs, ys = _extract_landmarks(
        result.face_landmarks[0], crop_rgb, x_offset, y_offset, frame_w, frame_h
    )
    blend = _extract_blendshapes(result.face_blendshapes[0]) if result.face_blendshapes else {}

    return _build_face_features(abs_landmarks, xs, ys, blend, result, frame_w, frame_h, x_offset, y_offset, crop_w, crop_h)