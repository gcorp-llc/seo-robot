from datetime import datetime
import asyncio
import random
from playwright.async_api import Page, ElementHandle
from typing import List, Dict, Optional

from config.crawler_settings import (
    MAX_RESULTS_TO_CHECK,
    MAX_SCROLL_ROUNDS,
)
from config.general_settings import PAGE_LOAD_TIMEOUT
from core.logger import logger
from core.performance_monitor import performance_monitor
from human.captcha import handle_captcha
from human.behavior import random_interactions
from core.utils import is_valid_url
from .interceptors import intercept_route

async def perform_search(page: Page, engine_name: str, keyword: str) -> List[Dict]:
    """
    Performs search and handles pagination if site is not found on page 1.
    """
    from config.search_engines import get_search_engines

    engines = get_search_engines(keyword)
    engine_config = next((e for e in engines if e['name'].lower() == engine_name.lower()), None)

    if not engine_config:
        logger.error(f"Engine {engine_name} configuration not found.")
        return []

    results = []
    max_pages = 3 # Look up to 3 pages

    for current_page in range(1, max_pages + 1):
        logger.info(f"🔍 Searching {engine_name} - Page {current_page} for '{keyword}'...")

        page_results = await search_in_engine_page(page, engine_config, current_page)
        results.extend(page_results)

        # In a real scenario, we might want to check if the target domain is in page_results
        # and stop if found. But for now, we return all found results.

        # Handle pagination click
        if current_page < max_pages:
            success = await go_to_next_page(page, engine_name)
            if not success:
                logger.info("No more pages found or failed to navigate.")
                break
            await asyncio.sleep(random.uniform(3, 6))

    return results

async def search_in_engine_page(page: Page, engine_config: Dict, page_num: int) -> List[Dict]:
    """Extracts results from a single page of search engine."""
    engine_name = engine_config["name"]
    url = engine_config["url"]
    selectors = engine_config["selectors"]
    exclude_domains = engine_config.get("exclude_domains", [])

    try:
        if page_num == 1:
            await page.route("**/*", intercept_route)
            await page.goto(url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)

        await asyncio.sleep(random.uniform(2, 4))

        # Check for captcha
        content_lower = (await page.content()).lower()
        if any(kw in content_lower for kw in ["captcha", "robot", "unusual traffic", "verify"]):
            if not await handle_captcha(page, engine_name):
                return []
            await asyncio.sleep(2)

        await random_interactions(page)

        working_locator = None
        working_selector = None

        for selector in selectors:
            try:
                # Wait briefly
                await page.wait_for_selector(selector, timeout=5000)
                count = await page.locator(selector).count()
                if count > 0:
                    working_locator = page.locator(selector)
                    working_selector = selector
                    break
            except:
                continue

        if not working_locator:
            return []

        results = []
        anchors = await working_locator.element_handles()

        for i, anchor in enumerate(anchors):
            try:
                href = await anchor.get_attribute("href")
                title = await anchor.inner_text()

                if href and is_valid_url(href, exclude_domains):
                    results.append({
                        "rank": (page_num - 1) * 10 + i + 1,
                        "url": href,
                        "title": title.strip() if title else "No Title",
                        "selector": working_selector,
                        "element": anchor,
                    })
            except:
                continue

        return results

    except Exception as e:
        logger.error(f"Error in {engine_name} page {page_num}: {e}")
        return []

async def go_to_next_page(page: Page, engine_name: str) -> bool:
    """Attempts to click 'Next' page button."""
    next_selectors = {
        "Google": "a#pnnext, a[aria-label='Next page']",
        "Bing": "a.sb_pagN, a[title='Next page']",
        "DuckDuckGo": "button#more-results",
        "Yandex": "a.pager__item_kind_next",
        "Yahoo": "a.next",
        "Brave": "a#next-pagination",
    }

    selector = next_selectors.get(engine_name)
    if not selector:
        return False

    try:
        next_btn = await page.query_selector(selector)
        if next_btn and await next_btn.is_visible():
            logger.info(f"Moving to next page in {engine_name}...")
            await next_btn.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await next_btn.click()
            return True
    except:
        pass
    return False
