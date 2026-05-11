from fastapi import APIRouter

from app.api.routes.upload_video import router as upload_router
from app.api.routes.stream_video import router as stream_router
from app.api.routes.roi import router as roi_router

api_router = APIRouter()

api_router.include_router(upload_router)
api_router.include_router(stream_router)
api_router.include_router(roi_router)