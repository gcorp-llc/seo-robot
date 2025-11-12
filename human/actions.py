import random
import asyncio
from playwright.async_api import Page

from config.human_settings import SCROLL_DELAY_RANGE

async def scroll_page_naturally(page: Page):
    """اسکرول طبیعی صفحه با رفتار انسانی"""
    try:
        # تعداد تصادفی اسکرول
        num_scrolls = random.randint(3, 6)
        
        for i in range(num_scrolls):
            # اسکرول به اندازه نصف صفحه
            scroll_amount = random.randint(300, 600)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            
            # تاخیر تصادفی بین اسکرول‌ها
            delay = random.uniform(*SCROLL_DELAY_RANGE)
            await asyncio.sleep(delay)
            
            # گاهی اسکرول کمی به بالا (رفتار انسانی)
            if random.random() < 0.2:  # 20% شانس
                back_scroll = random.randint(-200, -50)
                await page.evaluate(f"window.scrollBy(0, {back_scroll})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # در پایان، گاهی به بالای صفحه برگرد
        if random.random() < 0.3:  # 30% شانس
            await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await asyncio.sleep(random.uniform(1, 2))
            
    except Exception as e:
        # نادیده گرفتن خطاهای JS
        pass


async def move_mouse_naturally(page: Page):
    """حرکت تصادفی موس برای شبیه‌سازی رفتار انسانی"""
    try:
        num_movements = random.randint(2, 5)
        
        for _ in range(num_movements):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            
            # حرکت موس با سرعت تصادفی
            steps = random.randint(5, 15)
            await page.mouse.move(x, y, steps=steps)
            
            await asyncio.sleep(random.uniform(0.3, 1.0))
            
    except Exception:
        pass


async def random_page_interactions(page: Page):
    """تعاملات تصادفی با صفحه (کلیک، هاور، انتخاب متن)"""
    try:
        # حرکت موس
        await move_mouse_naturally(page)
        
        # گاهی روی یک المان هاور کن
        if random.random() < 0.4:  # 40% شانس
            try:
                # پیدا کردن المان‌های قابل کلیک
                clickable = await page.query_selector_all("a, button, [role='button']")
                if clickable and len(clickable) > 0:
                    element = random.choice(clickable)
                    await element.hover()
                    await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception:
                pass
        
        # گاهی یک متن را انتخاب کن (Ctrl+A نه، فقط drag)
        if random.random() < 0.2:  # 20% شانس
            try:
                paragraphs = await page.query_selector_all("p, h1, h2, h3, span")
                if paragraphs and len(paragraphs) > 0:
                    element = random.choice(paragraphs)
                    box = await element.bounding_box()
                    if box:
                        # شبیه‌سازی انتخاب متن با drag
                        start_x = box["x"] + 10
                        start_y = box["y"] + 10
                        end_x = box["x"] + box["width"] - 10
                        end_y = box["y"] + 10
                        
                        await page.mouse.move(start_x, start_y)
                        await page.mouse.down()
                        await page.mouse.move(end_x, end_y, steps=10)
                        await page.mouse.up()
                        await asyncio.sleep(random.uniform(0.5, 1.0))
            except Exception:
                pass
                
    except Exception:
        pass