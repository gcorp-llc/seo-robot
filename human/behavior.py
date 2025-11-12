import random
import asyncio
from playwright.async_api import Page

from config.human_settings import (
    MOUSE_MOVEMENTS_RANGE,
    CLICK_CHANCE,
    BACK_TO_TOP_CHANCE,
    INTERACTION_DELAY_RANGE
)


async def random_interactions(page: Page):
    """تعاملات تصادفی کامل با صفحه: موس، کلیک، اسکرول"""
    try:
        # 1. حرکات تصادفی موس
        num_movements = random.randint(*MOUSE_MOVEMENTS_RANGE)
        
        for _ in range(num_movements):
            x = random.randint(50, 1000)
            y = random.randint(50, 800)
            
            # حرکت موس به صورت نرم
            steps = random.randint(10, 25)
            await page.mouse.move(x, y, steps=steps)
            
            # تاخیر بین حرکات
            await asyncio.sleep(random.uniform(*INTERACTION_DELAY_RANGE))
        
        # 2. کلیک تصادفی روی المان‌ها
        if random.random() < CLICK_CHANCE:
            try:
                # پیدا کردن المان‌های قابل کلیک (بدون لینک‌ها)
                clickable_elements = await page.query_selector_all(
                    "button:not([type='submit']), [role='button'], div[onclick], span[onclick]"
                )
                
                if clickable_elements and len(clickable_elements) > 0:
                    element = random.choice(clickable_elements)
                    
                    # اطمینان از اینکه المان قابل مشاهده است
                    if await element.is_visible():
                        await element.hover()
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                        await element.click(force=True)
                        await asyncio.sleep(random.uniform(1.0, 2.5))
            except Exception:
                # اگر کلیک ناموفق بود، ادامه بده
                pass
        
        # 3. بازگشت به بالای صفحه
        if random.random() < BACK_TO_TOP_CHANCE:
            try:
                # اسکرول به بالا با انیمیشن
                await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
                await asyncio.sleep(random.uniform(1.5, 3.0))
            except Exception:
                pass
        
        # 4. هاور تصادفی روی المان‌ها
        if random.random() < 0.5:  # 50% شانس
            try:
                hoverable = await page.query_selector_all("a, img, div, p, h1, h2, h3")
                if hoverable and len(hoverable) > 0:
                    for _ in range(random.randint(1, 3)):
                        element = random.choice(hoverable)
                        if await element.is_visible():
                            await element.hover()
                            await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception:
                pass
                
    except Exception as e:
        # لاگ نکن، فقط ادامه بده
        pass


async def human_reading_behavior(page: Page, duration_seconds: float = None):
    """
    شبیه‌سازی رفتار خواندن انسان:
    - اسکرول آهسته
    - توقف در بخش‌های مختلف
    - حرکت موس
    """
    if duration_seconds is None:
        duration_seconds = random.uniform(10, 25)
    
    try:
        # تقسیم زمان به چند بخش
        num_sections = random.randint(3, 6)
        time_per_section = duration_seconds / num_sections
        
        for i in range(num_sections):
            # اسکرول به پایین
            scroll_amount = random.randint(200, 500)
            await page.evaluate(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")
            
            # توقف و خواندن
            read_time = time_per_section * random.uniform(0.7, 1.3)
            await asyncio.sleep(read_time)
            
            # گاهی موس را حرکت بده
            if random.random() < 0.6:
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y, steps=random.randint(5, 15))
            
            # گاهی کمی به عقب اسکرول کن (رفتار طبیعی)
            if random.random() < 0.25 and i > 0:
                back_scroll = random.randint(-150, -50)
                await page.evaluate(f"window.scrollBy({{top: {back_scroll}, behavior: 'smooth'}})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # در پایان، شانس بازگشت به بالا
        if random.random() < 0.3:
            await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await asyncio.sleep(random.uniform(1, 2))
            
    except Exception:
        pass