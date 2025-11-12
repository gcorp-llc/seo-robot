import random
from playwright.async_api import Page

from config.human_settings import MOUSE_MOVEMENTS_RANGE, CLICK_CHANCE, BACK_TO_TOP_CHANCE, INTERACTION_DELAY_RANGE

async def random_interactions(page: Page):
    num_movements = random.randint(*MOUSE_MOVEMENTS_RANGE)
    for _ in range(num_movements):
        # کد حرکت موس
        await asyncio.sleep(random.uniform(*INTERACTION_DELAY_RANGE))
    if random.random() < CLICK_CHANCE:
        # کلیک روی المان случайный
        pass
    if random.random() < BACK_TO_TOP_CHANCE:
        # بازگشت به بالا
        pass