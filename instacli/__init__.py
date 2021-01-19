import os, logging

BASE_DIR = f'{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/instacli'
PROGRESS_BAR = None
SCRAPED_LEN = 0

from instacli.models.settings import Settings
settings = Settings()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)

if settings.logging:
    LOGGER.setLevel(logging.DEBUG)
else:
    LOGGER.setLevel(logging.WARNING)

