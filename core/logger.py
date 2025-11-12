import logging
import os
from logging.handlers import RotatingFileHandler

from config.general_settings import LOG_LEVEL

class RotatingFileHandlerSafe(RotatingFileHandler):
    def __init__(self, filename, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'):
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount, encoding=encoding)
    
    def emit(self, record):
        try:
            super().emit(record)
        except Exception as e:
            print(f"خطا در لاگینگ: {e}")

log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

main_handler = RotatingFileHandlerSafe(
    filename=os.path.join(log_dir, 'seo_bot.log'),
    maxBytes=10*1024*1024,
    backupCount=5
)
main_handler.setFormatter(formatter)

error_log_handler = RotatingFileHandlerSafe(
    filename=os.path.join(log_dir, 'seo_bot_errors.log'),
    maxBytes=5*1024*1024,
    backupCount=3
)
error_log_handler.setLevel(logging.ERROR)
error_log_handler.setFormatter(formatter)

debug_handler = RotatingFileHandlerSafe(
    filename=os.path.join(log_dir, 'seo_bot_debug.log'),
    maxBytes=20*1024*1024,
    backupCount=2
)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(formatter)

performance_handler = RotatingFileHandlerSafe(
    filename=os.path.join(log_dir, 'seo_bot_performance.log'),
    maxBytes=15*1024*1024,
    backupCount=4
)
performance_handler.setLevel(logging.INFO)
performance_handler.setFormatter(formatter)

logger = logging.getLogger('SEOBot')
logger.setLevel(getattr(logging, LOG_LEVEL))

for handler in logger.handlers[:]:
    logger.removeHandler(handler)

logger.addHandler(main_handler)
logger.addHandler(error_log_handler)
logger.addHandler(debug_handler)
logger.addHandler(performance_handler)
logger.addHandler(logging.StreamHandler())

logging.getLogger('playwright').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

logger.info(f"✅ سیستم لاگ‌ با rotating file handler راه‌اندازی شد")