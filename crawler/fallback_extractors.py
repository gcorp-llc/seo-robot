import re
from playwright.async_api import Page
from typing import List

from core.utils import is_valid_url

async def extract_urls_from_text(page: Page, exclude_domains: List[str]) -> List[str]:
    try:
        page_text = await page.inner_text('body')
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w .-]*/?'
        found_urls = re.findall(url_pattern, page_text)
        valid_urls = [u for u in found_urls if is_valid_url(u, exclude_domains)]
        return list(set(valid_urls))[:20]
    except Exception as e:
        from core.logger import logger
        logger.error(f"   خطا در استخراج URL از متن: {e}")
        return []

async def extract_urls_from_meta(page: Page, exclude_domains: List[str]) -> List[str]:
    urls = []
    try:
        metas = await page.locator('meta[property="og:url"], meta[name="twitter:url"]').all()
        for meta in metas:
            content = await meta.get_attribute('content')
            if content and is_valid_url(content, exclude_domains):
                urls.append(content)
    except Exception as e:
        from core.logger import logger
        logger.error(f"   خطا در متا: {e}")
    return list(set(urls))[:10]

async def extract_urls_from_scripts(page: Page, exclude_domains: List[str]) -> List[str]:
    urls = []
    try:
        scripts = await page.locator('script').all()
        for script in scripts:
            content = await script.inner_text()
            matches = re.findall(r'https?://[^"\']+', content)
            urls.extend([u for u in matches if is_valid_url(u, exclude_domains)])
    except Exception as e:
        from core.logger import logger
        logger.error(f"   خطا در اسکریپت‌ها: {e}")
    return list(set(urls))[:10]

async def extract_urls_from_images(page: Page, exclude_domains: List[str]) -> List[str]:
    urls = []
    try:
        images = await page.locator('img').all()
        for img in images:
            src = await img.get_attribute('src')
            alt = await img.get_attribute('alt')
            if src and is_valid_url(src, exclude_domains):
                urls.append(src)
            if alt and re.match(r'https?://', alt):
                urls.append(alt)
    except Exception as e:
        from core.logger import logger
        logger.error(f"   خطا در تصاویر: {e}")
    return list(set(urls))[:10]