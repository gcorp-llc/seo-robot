import random
import asyncio
import math
from playwright.async_api import Page

from config.human_settings import SCROLL_DELAY_RANGE

async def bezier_curve(p0, p1, p2, p3, t):
    """Calculates a point on a cubic Bezier curve at time t [0, 1]."""
    return (
        (1 - t)**3 * p0 +
        3 * (1 - t)**2 * t * p1 +
        3 * (1 - t) * t**2 * p2 +
        t**3 * p3
    )

async def move_mouse_bezier(page: Page, target_x: float, target_y: float, steps: int = 25):
    """Moves mouse to target_x, target_y using a cubic Bezier curve."""
    try:
        # Get current mouse position (approximate if not known)
        current_pos = await page.evaluate("""
            () => ({ x: window.lastMouseX || 100, y: window.lastMouseY || 100 })
        """)
        start_x, start_y = current_pos['x'], current_pos['y']

        # Control points for Bezier curve
        p1_x = start_x + (target_x - start_x) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        p1_y = start_y + (target_y - start_y) * random.uniform(0.1, 0.4) + random.randint(-50, 50)

        p2_x = start_x + (target_x - start_x) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
        p2_y = start_y + (target_y - start_y) * random.uniform(0.6, 0.9) + random.randint(-50, 50)

        for i in range(steps + 1):
            t = i / steps
            # Add some easing
            t_eased = t * t * (3 - 2 * t)

            x = await bezier_curve(start_x, p1_x, p2_x, target_x, t_eased)
            y = await bezier_curve(start_y, p1_y, p2_y, target_y, t_eased)

            # Add micro-jitter
            if random.random() < 0.1:
                x += random.uniform(-1, 1)
                y += random.uniform(-1, 1)

            await page.mouse.move(x, y)

            # Update position in window for next call
            if i % 5 == 0 or i == steps:
                await page.evaluate(f"window.lastMouseX = {x}; window.lastMouseY = {y};")

            await asyncio.sleep(random.uniform(0.005, 0.015))
    except Exception:
        # Fallback to simple move
        await page.mouse.move(target_x, target_y)

async def scroll_page_naturally(page: Page):
    """Natural scrolling with acceleration and deceleration."""
    try:
        num_scrolls = random.randint(4, 8)
        total_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = await page.evaluate("window.innerHeight")

        for _ in range(num_scrolls):
            current_scroll = await page.evaluate("window.scrollY")
            if current_scroll + viewport_height >= total_height - 100:
                break

            target_scroll = random.randint(300, 700)
            steps = random.randint(15, 30)

            for i in range(steps):
                # Easing function for smoother scroll
                fraction = (i + 1) / steps
                step_scroll = target_scroll / steps

                # Vary speed
                wait = random.uniform(0.01, 0.03)
                await page.evaluate(f"window.scrollBy(0, {step_scroll})")
                await asyncio.sleep(wait)

            # Random pause after a scroll block
            await asyncio.sleep(random.uniform(*SCROLL_DELAY_RANGE))

            # Occasional small back-scroll (human behavior)
            if random.random() < 0.15:
                back_steps = random.randint(5, 10)
                back_amount = random.randint(-150, -50)
                for _ in range(back_steps):
                    await page.evaluate(f"window.scrollBy(0, {back_amount/back_steps})")
                    await asyncio.sleep(0.02)
                await asyncio.sleep(random.uniform(0.5, 1.0))

    except Exception:
        pass

async def handle_common_popups(page: Page):
    """Tries to dismiss common cookie consents and popups."""
    popups_selectors = [
        "button[id*='cookie']", "button[class*='cookie']",
        "button[id*='accept']", "button[class*='accept']",
        "a[class*='close']", "button[class*='close']",
        ".modal-close", ".popup-close", "#onesignal-slidedown-cancel-button"
    ]
    try:
        for selector in popups_selectors:
            elements = await page.query_selector_all(selector)
            for el in elements:
                if await el.is_visible():
                    # Human-like click
                    box = await el.bounding_box()
                    if box:
                        await move_mouse_bezier(page, box['x'] + box['width']/2, box['y'] + box['height']/2)
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                        await el.click()
                        await asyncio.sleep(random.uniform(1, 2))
                        return # Handle one at a time
    except Exception:
        pass

async def random_page_interactions(page: Page):
    """Enhanced random interactions: move, hover, selective text dragging."""
    try:
        # Move mouse several times
        for _ in range(random.randint(2, 4)):
            tx = random.randint(0, 1280)
            ty = random.randint(0, 720)
            await move_mouse_bezier(page, tx, ty)
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # Random Hover
        if random.random() < 0.5:
            elements = await page.query_selector_all("a, button, h2, p")
            if elements:
                target = random.choice(elements)
                if await target.is_visible():
                    box = await target.bounding_box()
                    if box:
                        await move_mouse_bezier(page, box['x'] + box['width']/2, box['y'] + box['height']/2)
                        await asyncio.sleep(random.uniform(0.8, 2.0))

        # Random highlight (simulating reading/interest)
        if random.random() < 0.2:
            paragraphs = await page.query_selector_all("p")
            if paragraphs:
                p = random.choice(paragraphs)
                box = await p.bounding_box()
                if box and box['height'] > 20:
                    start_x = box['x'] + random.randint(10, 50)
                    start_y = box['y'] + 10
                    end_x = start_x + random.randint(50, 200)
                    end_y = start_y

                    await move_mouse_bezier(page, start_x, start_y)
                    await page.mouse.down()
                    await move_mouse_bezier(page, end_x, end_y, steps=10)
                    await page.mouse.up()
                    await asyncio.sleep(random.uniform(0.5, 1.5))

    except Exception:
        pass
