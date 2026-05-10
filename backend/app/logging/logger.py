"""Logging configuration for FaceFeat."""

import logging
import os
from datetime import datetime

from backend.app.core.config import settings

RUN_TIMESTAMP = datetime.now()
LOG_FILE = f"{RUN_TIMESTAMP.strftime('%d_%m_%Y_%H:%M:%S')}.log"
LOGS_PATH = os.path.join(settings.PROJECT_ROOT, "logs", RUN_TIMESTAMP.strftime("%d_%m_%Y_%H:%M"))
os.makedirs(LOGS_PATH, exist_ok=True)

LOG_FILE_PATH = os.path.join(LOGS_PATH, LOG_FILE)

logging.basicConfig(
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler(),
    ],
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)