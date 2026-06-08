import random
import asyncio
from playwright.async_api import Page
from .actions import move_mouse_bezier, random_page_interactions, scroll_page_naturally, handle_common_popups

from config.human_settings import (
    MOUSE_MOVEMENTS_RANGE,
    CLICK_CHANCE,
    BACK_TO_TOP_CHANCE,
    INTERACTION_DELAY_RANGE,
)

async def random_interactions(page: Page):
    """Full natural interaction set."""
    try:
        # Dismiss popups first
        await handle_common_popups(page)

        # Random mouse movements
        num_movements = random.randint(*MOUSE_MOVEMENTS_RANGE)
        for _ in range(num_movements):
            tx = random.randint(50, 1000)
            ty = random.randint(50, 800)
            await move_mouse_bezier(page, tx, ty)
            await asyncio.sleep(random.uniform(*INTERACTION_DELAY_RANGE))

        # Random clicks on non-navigation elements
        if random.random() < CLICK_CHANCE:
            clickable = await page.query_selector_all("div[id], span, label")
            if clickable:
                target = random.choice(clickable)
                if await target.is_visible():
                    box = await target.bounding_box()
                    if box and box['width'] < 300: # Don't click huge containers
                        await move_mouse_bezier(page, box['x']+box['width']/2, box['y']+box['height']/2)
                        await page.mouse.click(box['x']+box['width']/2, box['y']+box['height']/2)
                        await asyncio.sleep(random.uniform(1.0, 2.0))

        # Random interactions (hover, drag)
        await random_page_interactions(page)

        # Back to top?
        if random.random() < BACK_TO_TOP_CHANCE:
            await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await asyncio.sleep(random.uniform(1.5, 3.0))

    except Exception:
        pass

async def human_reading_behavior(page: Page, duration_seconds: float = None):
    """Simulates a human reading a page."""
    if duration_seconds is None:
        duration_seconds = random.uniform(15, 40) # Increased duration

    start_time = asyncio.get_event_loop().time()
    try:
        while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
            # Chance to scroll
            if random.random() < 0.7:
                scroll_amount = random.randint(150, 400)
                await page.evaluate(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")
                await asyncio.sleep(random.uniform(2, 5))

            # Chance to move mouse
            if random.random() < 0.4:
                tx = random.randint(100, 900)
                ty = random.randint(100, 700)
                await move_mouse_bezier(page, tx, ty)

            # Chance to just wait (reading)
            await asyncio.sleep(random.uniform(3, 8))

            # 10% chance to look at something specific
            if random.random() < 0.1:
                await random_page_interactions(page)

    except Exception:
        pass
