import asyncio
from urllib.parse import urlparse, urljoin
from playwright.async_api import Page
from typing import List

from core.logger import logger


async def extract_internal_links(
    page: Page,
    current_url: str,
    target_domain: str,
    max_links: int = 50
) -> List[str]:
    """
    استخراج لینک‌های داخلی از صفحه فعلی
    
    Args:
        page: صفحه Playwright
        current_url: URL فعلی
        target_domain: دامنه هدف
        max_links: حداکثر تعداد لینک‌ها
    
    Returns:
        لیست URLهای داخلی یکتا
    """
    try:
        # پیدا کردن تمام تگ‌های <a>
        anchors = await page.query_selector_all("a[href]")
        
        if not anchors:
            logger.debug("هیچ لینکی یافت نشد")
            return []
        
        internal_links = []
        seen_urls = set()
        
        for anchor in anchors:
            try:
                href = await anchor.get_attribute("href")
                
                if not href or href in seen_urls:
                    continue
                
                # نرمال‌سازی URL
                absolute_url = urljoin(current_url, href)
                parsed = urlparse(absolute_url)
                
                # فیلتر کردن:
                # 1. باید HTTP/HTTPS باشد
                if parsed.scheme not in ["http", "https"]:
                    continue
                
                # 2. باید از دامنه هدف باشد
                if not parsed.netloc.lower().endswith(target_domain.lower()):
                    continue
                
                # 3. نباید همان صفحه فعلی باشد
                if absolute_url == current_url:
                    continue
                
                # 4. فیلتر فایل‌های غیرمفید
                excluded_extensions = ['.pdf', '.zip', '.jpg', '.png', '.gif', '.mp4', '.mp3']
                if any(parsed.path.lower().endswith(ext) for ext in excluded_extensions):
                    continue
                
                # 5. فیلتر لینک‌های خاص (login, admin, etc.)
                excluded_keywords = ['login', 'signin', 'register', 'admin', 'logout', 'cart', 'checkout']
                if any(keyword in parsed.path.lower() for keyword in excluded_keywords):
                    continue
                
                seen_urls.add(href)
                internal_links.append(absolute_url)
                
                if len(internal_links) >= max_links:
                    break
                    
            except Exception as e:
                logger.debug(f"خطا در پردازش لینک: {e}")
                continue
        
        logger.debug(f"✅ {len(internal_links)} لینک داخلی استخراج شد")
        return internal_links
        
    except Exception as e:
        logger.error(f"❌ خطا در استخراج لینک‌ها: {e}")
        return []