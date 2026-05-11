import sys
import uuid
from fastapi import APIRouter, UploadFile, File, Depends
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.exceptions.exception import FaceFeatException
from app.logging.logger import logging
from app.models.video import Video
from app.services.video_processor import process_video

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

        video_id = uuid.uuid4()
        input_path = settings.UPLOAD_DIR / f"{video_id}.mp4"
        output_path = settings.PROCESSED_DIR / f"{video_id}.mp4"

        # save input file
        with open(input_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        logger.info(f"Video saved to disk: {input_path}")

        video = Video(
            id=video_id,
            fps=0,
            frame_count=0,
            original_path=str(input_path),
            processed_path="",
        )
        session.add(video)
        session.commit()

        # detect face, draw ROI, update DB
        process_video(video_id, input_path, output_path, session)

        return {"video_id": str(video_id), "filename": file.filename}

    except Exception as e:
        raise FaceFeatException(str(e), sys)