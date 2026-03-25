import logging
import os
from datetime import datetime
from src.core.config import settings

os.makedirs(os.path.join(settings.BASE_DIR, "logs"), exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(settings.BASE_DIR, "logs", f"app_{datetime.now().strftime('%Y%m%d')}.log")
        ),
    ],
)

logger = logging.getLogger("iptv_panel")
