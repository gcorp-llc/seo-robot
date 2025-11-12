from playwright.async_api import Page
from typing import List

from config.crawler_settings import get_deep_crawl_selectors
from core.utils import is_same_domain, urljoin

async def extract_internal_links(page: Page, current_url: str, target_domain: str) -> List[str]:
    selectors = get_deep_crawl_selectors(target_domain)
    internal_links = []
    for selector in selectors:
        try:
            anchors = await page.locator(selector).all()
            for anchor in anchors:
                href = await anchor.get_attribute('href')
                if href:
                    full_url = urljoin(current_url, href)
                    if is_same_domain(full_url, target_domain):
                        internal_links.append(full_url)
        except Exception:
            pass
    return list(set(internal_links))