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


async def search_in_engine(
    page: Page,
    engine_config: Dict,
    max_results: int = MAX_RESULTS_TO_CHECK
) -> List[Dict]:  # ✅ تغییر: برمی‌گرداند Dict با selector
    """
    جستجو در موتور و استخراج نتایج با اطلاعات کامل
    
    Returns:
        List[Dict]: لیست نتایج با format:
        {
            'rank': int,
            'url': str,
            'title': str,
            'selector': str,  # ✅ اضافه شد
            'element': ElementHandle  # ✅ اضافه شد
        }
    """
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
        
        # ✅ اضافه: صبر برای networkidle
        await page.goto(url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        await asyncio.sleep(random.uniform(3, 5))  # ✅ تاخیر بیشتر
        
        # ✅ اضافه: بررسی JavaScript
        await page.evaluate("() => document.readyState")
        
        # بررسی کپچا
        content_lower = (await page.content()).lower()
        if any(kw in content_lower for kw in ['captcha', 'robot', 'unusual traffic', 'verify']):
            performance_monitor.record_captcha()
            if not await handle_captcha(page, engine_name):
                return []
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(3)
        
        # رفتار انسانی اولیه
        await random_interactions(page)
        
        # یافتن سلکتور کارآمد
        working_locator = None
        working_selector = None
        
        priority_selectors = engine_config.get("priority_selectors", [])
        if priority_selectors:
            for selector in priority_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=8000)
                    count = await page.locator(selector).count()
                    if count > 0:
                        working_locator = page.locator(selector)
                        working_selector = selector
                        logger.info(f"   ✅ سلکتور اولویت‌دار: {count} نتیجه")
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
                        working_selector = selector
                        logger.info(f"   ✅ سلکتور عادی: {count} نتیجه")
                        break
                except Exception:
                    continue
        
        if not working_locator:
            logger.error(f"   ❌ هیچ سلکتوری کار نکرد!")
            return []
        
        # ✅ استخراج نتایج با اطلاعات کامل
        for scroll_round in range(MAX_SCROLL_ROUNDS):
            anchors = await working_locator.element_handles()  # ✅ تغییر: استفاده از element_handles
            new_links = 0
            
            for anchor in anchors:
                try:
                    href = await anchor.get_attribute('href')
                    title = await anchor.inner_text()  # ✅ اضافه شد
                    
                    if href and is_valid_url(href, exclude_domains):
                        if href not in seen_urls:
                            seen_urls.add(href)
                            
                            # ✅ ذخیره اطلاعات کامل
                            results.append({
                                'rank': rank,
                                'url': href,
                                'title': title.strip() if title else "بدون عنوان",
                                'selector': working_selector,
                                'element': anchor  # ✅ ذخیره reference المان
                            })
                            
                            rank += 1
                            new_links += 1
                            
                            if len(results) >= max_results:
                                break
                except Exception as e:
                    logger.debug(f"خطا در استخراج anchor: {e}")
                    continue
            
            logger.debug(f"      دور {scroll_round + 1}: {new_links} لینک جدید")
            
            if len(results) >= max_results:
                break
            
            # اسکرول با رفتار انسانی
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(2, 4))
        
        logger.info(f"   ✅ {len(results)} نتیجه یافت شد")
        
        if results:
            logger.debug(f"   📋 نمونه نتایج:")
            for r in results[:3]:
                logger.debug(f"      {r['rank']}. {r['title'][:40]}... - {r['url'][:60]}...")
        
        duration = (datetime.now() - start_time).total_seconds()
        performance_monitor.record_search(success=True, duration=duration)
        
        return results
        
    except Exception as e:
        logger.error(f"   ❌ خطا در {engine_name}: {e}")
        performance_monitor.record_search(success=False)
        performance_monitor.record_error(f"خطا در {engine_name}: {str(e)}")
        return []