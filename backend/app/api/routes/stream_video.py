import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.core.database import get_session
from app.logging.logger import logging
from app.models.video import Video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["video"])

CHUNK_SIZE = 1024 * 1024  # 1MB chunks


def _get_video_or_404(video_id: uuid.UUID, session: Session) -> Video:
    """Fetch video record from DB or raise 404."""
    video = session.get(Video, video_id)
    if not video:
        logger.warning(f"Video not found | video_id={video_id}")
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found.")
    return video


def _resolve_video_path(video: Video) -> Path:
    """Resolve and validate the processed video file path."""
    if not video.processed_path:
        logger.warning(f"No processed path on video | video_id={video.id}")
        raise HTTPException(status_code=404, detail="Processed video not available yet.")

    path = Path(video.processed_path)
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists() or not path.is_file():
        logger.error(f"Video file not found on disk | path={path} | video_id={video.id}")
        raise HTTPException(status_code=404, detail="Video file not found on disk.")

    return path


def _parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int]:
    """Parse HTTP Range header. Returns (start, end) byte positions."""
    if not range_header or not range_header.startswith("bytes="):
        return 0, file_size - 1

    try:
        range_val = range_header.removeprefix("bytes=")
        start_str, end_str = range_val.split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)
        start = max(0, start)
        return start, end
    except (ValueError, AttributeError):
        logger.warning(f"Malformed Range header: {range_header} — serving full file")
        return 0, file_size - 1


def _file_chunk_generator(path: Path, start: int, end: int):
    """Yield file content in chunks between byte positions start and end."""
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get("/{video_id}")
def stream_video(
    video_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    """
    Stream a processed video by ID with HTTP byte-range support.
    Supports browser <video> tag seeking via Range header.
    """
    logger.info(f"Stream request | video_id={video_id} | client={request.client.host}")

    try:
        video = _get_video_or_404(video_id, session)
        path = _resolve_video_path(video)

        file_size = path.stat().st_size
        range_header = request.headers.get("Range")
        start, end = _parse_range_header(range_header, file_size)
        content_length = end - start + 1
        is_partial = range_header is not None

        logger.info(
            f"Serving video | video_id={video_id} | "
            f"file={path.name} | size={file_size} | "
            f"range={start}-{end} | partial={is_partial}"
        )

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Disposition": f"inline; filename={path.name}",
        }

        return StreamingResponse(
            content=_file_chunk_generator(path, start, end),
            status_code=206 if is_partial else 200,
            media_type="video/mp4",
            headers=headers,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error streaming video | video_id={video_id} | error={e}")
        raise HTTPException(status_code=500, detail="Internal server error while streaming video.")


@router.get("/{video_id}/status")
def get_video_status(video_id: str, db: Session = Depends(get_session)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "video_id": video_id,
        "status": "done" if video.processed_path else "processing",
        "processed_path": video.processed_path,
    }