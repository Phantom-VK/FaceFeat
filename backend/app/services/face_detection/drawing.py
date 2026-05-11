import numpy as np
from PIL import Image, ImageDraw

from app.services.face_detection.config import COLORS


def draw_faces(frame: np.ndarray, faces: list[dict]) -> np.ndarray:
    """Draw bounding boxes, landmarks, and expression overlays for all faces."""
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)

    for face_idx, face in enumerate(faces):
        color = COLORS[face_idx % len(COLORS)]
        _draw_bbox_and_label(draw, face, face_idx, color)
        _draw_landmarks(draw, face, frame.shape, color)
        _draw_expression_overlay(draw, face, color)

    return np.array(img)


def _draw_bbox_and_label(draw: ImageDraw.ImageDraw, face: dict, face_idx: int, color: str):
    x1, y1 = int(face["x"]), int(face["y"])
    x2, y2 = x1 + int(face["w"]), y1 + int(face["h"])
    draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
    draw.text((x1, max(0, y1 - 16)), f"Face {face_idx + 1}", fill=color)


def _draw_landmarks(draw: ImageDraw.ImageDraw, face: dict, frame_shape: tuple, color: str):
    frame_h, frame_w = frame_shape[:2]
    for lm in face.get("landmarks", []):
        px, py = int(lm["x"]), int(lm["y"])
        if 0 <= px < frame_w and 0 <= py < frame_h:
            draw.ellipse([(px - 1, py - 1), (px + 1, py + 1)], fill=color)


def _draw_expression_overlay(draw: ImageDraw.ImageDraw, face: dict, color: str):
    x1, y1 = int(face["x"]), int(face["y"])
    overlay = []

    if face.get("smile_score") is not None:
        overlay.append(f"Smile:{face['smile_score']:.2f}")
    if face.get("blink_left") is not None and face.get("blink_right") is not None:
        overlay.append(f"Blink L/R:{face['blink_left']:.2f}/{face['blink_right']:.2f}")
    if face.get("pitch") is not None:
        overlay.append(f"P:{face['pitch']:.1f} Y:{face['yaw']:.1f} R:{face['roll']:.1f}")

    for i, line in enumerate(overlay):
        draw.text((x1, max(0, y1 - 34 - i * 14)), line, fill="yellow")