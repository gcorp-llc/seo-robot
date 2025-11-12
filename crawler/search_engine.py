from datetime import datetime
import asyncio
import random
import re

from playwright.async_api import Page
from typing import List, Tuple, Dict

from config.crawler_settings import MAX_RESULTS_TO_CHECK, MAX_SCROLL_ROUNDS, FALLBACK_STRATEGIES
from config.general_settings import PAGE_LOAD_TIMEOUT
from core.logger import logger
from core.performance_monitor import performance_monitor
from human.captcha import handle_captcha
from human.behavior import random_interactions
from .fallback_extractors import extract_urls_from_text, extract_urls_from_meta, extract_urls_from_scripts, extract_urls_from_images
from core.utils import is_valid_url
from .interceptors import intercept_route
from .page_visit import smart_click_and_visit

async def search_in_engine(
    page: Page,
    engine_config: Dict,
    max_results: int = MAX_RESULTS_TO_CHECK
) -> List[Tuple[int, str]]:
    start_time = datetime.now()
    engine_name = engine_config["name"]
    url = engine_config["url"]
    selectors = engine_config["selectors"]
    exclude_domains = engine_config.get("exclude_domains", [])
    logger.info(f"\n🔍 جستجو در {engine_name}...")
    results = []
    rank = 1
    seen_urls = set()
    try:
        await page.route("**/*", intercept_route)
        await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        await asyncio.sleep(random.uniform(2, 4))  # تاخیر انسانی
        content_lower = (await page.content()).lower()
        if any(kw in content_lower for kw in ['captcha', 'robot', 'unusual traffic', 'verify']):
            performance_monitor.record_captcha()
            if not await handle_captcha(page, engine_name):
                return []
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
        await random_interactions(page)
        working_locator = None
        priority_selectors = engine_config.get("priority_selectors", [])
        if priority_selectors:
            for selector in priority_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=8000)
                    count = await page.locator(selector).count()
                    if count > 0:
                        working_locator = page.locator(selector)
                        logger.info(f"   ✅ انتخابگر با اولویت کار کرد: {count} نتیجه")
                        break
                except Exception:
                    continue
        if not working_locator:
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=6000)
                    count = await page.locator(selector).count()
                    if count > 0:
                        working_locator = page.locator(selector)
                        logger.info(f"   ✅ انتخابگر کار کرد: {count} نتیجه")
                        break
                except Exception:
                    continue
        if not working_locator:
            logger.error(f"   ❌ هیچ انتخابگری کار نکرد!")
            if any(FALLBACK_STRATEGIES.values()):
                logger.info(f"   🔄 تلاش برای استخراج URL با استراتژی‌های fallback...")
                all_fallback_urls = []
                if FALLBACK_STRATEGIES.get("extract_from_text", True):
                    all_fallback_urls.extend(await extract_urls_from_text(page, exclude_domains))
                if FALLBACK_STRATEGIES.get("extract_from_meta", True):
                    all_fallback_urls.extend(await extract_urls_from_meta(page, exclude_domains))
                if FALLBACK_STRATEGIES.get("extract_from_scripts", True):
                    all_fallback_urls.extend(await extract_urls_from_scripts(page, exclude_domains))
                if FALLBACK_STRATEGIES.get("extract_from_images", True):
                    all_fallback_urls.extend(await extract_urls_from_images(page, exclude_domains))
                unique_urls = list(dict.fromkeys(all_fallback_urls))
                if unique_urls:
                    logger.info(f"   ✅ {len(unique_urls)} URL با استراتژی‌های fallback استخراج شد")
                    for u in unique_urls[:max_results]:
                        if u not in seen_urls:
                            seen_urls.add(u)
                            results.append((rank, u))
                            rank += 1
                    return results
            # ذخیره اسکرین‌شات اگر لازم
            from config.general_settings import SAVE_SCREENSHOTS, SCREENSHOT_DIR
            if SAVE_SCREENSHOTS:
                from pathlib import Path
                screenshot_path = Path(SCREENSHOT_DIR) / f"error_{engine_name}_{datetime.now():%H%M%S}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"   📸 اسکرین‌شات خطا: {screenshot_path}")
            return []
        for scroll_round in range(MAX_SCROLL_ROUNDS):
            anchors = await working_locator.all()
            new_links = 0
            for anchor in anchors:
                href = await anchor.get_attribute('href')
                if href and is_valid_url(href, exclude_domains):
                    if href not in seen_urls:
                        seen_urls.add(href)
                        results.append((rank, href))
                        rank += 1
                        new_links += 1
                        if len(results) >= max_results:
                            break
            logger.debug(f"      دور {scroll_round + 1}: {new_links} لینک جدید")
            if len(results) >= max_results:
                break
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(2, 4))
        logger.info(f"   ✅ {len(results)} نتیجه یافت شد")
        if results:
            logger.debug(f"   📋 نمونه نتایج:")
            for r, link in results[:3]:
                logger.debug(f"      {r}. {link[:60]}...")
        
        duration = (datetime.now() - start_time).total_seconds()
        performance_monitor.record_search(success=True, duration=duration)
        
        return results
    except Exception as e:
        logger.error(f"   ❌ خطا در {engine_name}: {e}")
        performance_monitor.record_search(success=False)
        performance_monitor.record_error(f"خطا در {engine_name}: {str(e)}")
        return []