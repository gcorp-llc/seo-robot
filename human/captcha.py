from playwright.async_api import Page

from config.general_settings import CAPTCHA_MAX_WAIT
from core.logger import logger

async def handle_captcha(page: Page, engine_name: str) -> bool:
    try:
        # کد حل کپچا، اگر لازم
        await asyncio.sleep(CAPTCHA_MAX_WAIT)
        return True
    except Exception as e:
        logger.error(f"❌ خطا در حل کپچا برای {engine_name}: {e}")
        return False