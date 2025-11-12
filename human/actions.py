import random
from playwright.async_api import Page

from config.human_settings import SCROLL_DELAY_RANGE

async def scroll_page_naturally(page: Page):
    # اسکرول طبیعی
    for _ in range(random.randint(3, 6)):
        await page.evaluate("window.scrollBy(0, window.innerHeight / 2)")
        await asyncio.sleep(random.uniform(*SCROLL_DELAY_RANGE))