import numpy as np


def safe_float(value, default: float = 0.0) -> float:
    """Convert value to float safely, returning default on None or error."""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def pose_from_matrix(matrix_data) -> tuple[float | None, float | None, float | None]:
    """Extract pitch, yaw, roll from a 4x4 facial transformation matrix."""
    try:
        m = np.array(matrix_data).reshape(4, 4)
        pitch = float(np.degrees(np.arcsin(np.clip(-m[2][1], -1.0, 1.0))))
        yaw   = float(np.degrees(np.arctan2(m[2][0], m[2][2])))
        roll  = float(np.degrees(np.arctan2(m[0][1], m[1][1])))
        return pitch, yaw, roll
    except Exception:
        return None, None, None