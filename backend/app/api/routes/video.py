import sys
import uuid

from fastapi import APIRouter, UploadFile, File, Depends
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.exceptions.exception import FaceFeatException
from app.logging.logger import logging
from app.models.video import Video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    try:
        logger.info(f"Received upload request for file: {file.filename}")

        if not file.filename.endswith((".mp4", ".webm", ".mkv")):
            raise ValueError(f"Unsupported file format: {file.filename}")

        video_id = str(uuid.uuid4())
        input_path = settings.UPLOAD_DIR / f"{video_id}.mp4"

        with open(input_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        logger.info(f"Video saved to disk: {input_path}")

        # Insert DB record — fps and frame_count are 0 for now, updated after processing
        video = Video(
            id=uuid.UUID(video_id),
            fps=0,
            frame_count=0,
            original_path=str(input_path),
            processed_path="",
        )
        session.add(video)
        session.commit()
        session.refresh(video)

        logger.info(f"Video record inserted in DB with id: {video_id}")

        return {"video_id": video_id, "filename": file.filename}

    except Exception as e:
        raise FaceFeatException(str(e), sys)