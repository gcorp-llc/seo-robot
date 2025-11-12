import asyncio
import random
from datetime import datetime

from playwright.async_api import Page
from typing import List

from config.human_settings import STAY_ON_PAGE_RANGE, BETWEEN_PAGES_DELAY
from core.logger import logger
from core.performance_monitor import performance_monitor
from human.actions import scroll_page_naturally
from human.behavior import random_interactions
from .link_extractor import extract_internal_links

async def visit_page_naturally(page: Page, url: str, target_domain: str, is_from_search: bool = True) -> bool:
    start_time = datetime.now()
    try:
        if is_from_search:
            # کلیک طبیعی اگر از جستجو باشد
            pass  # کد کلیک اگر لازم
        else:
            await page.goto(url, wait_until="domcontentloaded")
        
        await random_interactions(page)
        await scroll_page_naturally(page)
        
        stay_time = random.uniform(*STAY_ON_PAGE_RANGE)
        await asyncio.sleep(stay_time)
        
        duration = (datetime.now() - start_time).total_seconds()
        performance_monitor.record_visit(success=True, duration=duration)
        return True
    except Exception as e:
        logger.error(f"❌ خطا در بازدید صفحه {url}: {e}")
        performance_monitor.record_visit(success=False)
        return False

async def smart_click_and_visit(page: Page, results: List[Tuple[int, str]], target_domain: str, search_url: str):
    target_results = [(rank, url) for rank, url in results if is_same_domain(url, target_domain)]
    if target_results:
        # انتخاب و کلیک روی لینک هدف
        for rank, url in target_results:
            logger.info(f"🎯 یافتن لینک هدف در رتبه {rank}: {url}")
            await visit_page_naturally(page, url, target_domain, is_from_search=True)
            # بازدید لینک‌های داخلی
            internal_links = await extract_internal_links(page, url, target_domain)
            if internal_links:
                num_internal = min(2, len(internal_links))
                selected_internal = random.sample(internal_links, num_internal)
                for internal_url in selected_internal:
                    await asyncio.sleep(random.uniform(*BETWEEN_PAGES_DELAY))
                    await visit_page_naturally(page, internal_url, target_domain, is_from_search=False)