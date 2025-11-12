import random
import asyncio
from urllib.parse import urlparse
from playwright.async_api import Page
from typing import Optional

from core.logger import logger
from human.behavior import random_interactions, human_reading_behavior
from human.actions import scroll_page_naturally, random_page_interactions
from crawler.link_extractor import extract_internal_links


async def visit_page_naturally(
    page: Page,
    url: str,
    target_domain: str,
    is_from_search: bool = False
) -> bool:
    """
    بازدید طبیعی از یک صفحه با رفتار کاملاً انسانی
    
    Args:
        page: صفحه Playwright
        url: URL مقصد
        target_domain: دامنه هدف
        is_from_search: آیا از نتایج جستجو آمده؟
    
    Returns:
        True اگر موفق، False در غیر این صورت
    """
    try:
        logger.info(f"🌐 بازدید از: {url}")
        
        # 1. رفتن به صفحه
        response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        if not response or response.status >= 400:
            logger.warning(f"⚠️ خطای HTTP {response.status if response else 'None'} برای {url}")
            return False
        
        # 2. صبر برای بارگذاری کامل
        await asyncio.sleep(random.uniform(1.5, 3.0))
        
        # 3. اسکرول اولیه (مشاهده اولیه صفحه)
        logger.debug("📜 اسکرول اولیه...")
        await scroll_page_naturally(page)
        
        # 4. رفتار خواندن انسانی (توقف، اسکرول، حرکت موس)
        reading_duration = random.uniform(8, 20) if is_from_search else random.uniform(5, 15)
        logger.debug(f"📖 شبیه‌سازی خواندن برای {reading_duration:.1f} ثانیه...")
        await human_reading_behavior(page, reading_duration)
        
        # 5. تعاملات تصادفی (کلیک، هاور، حرکت موس)
        if random.random() < 0.7:  # 70% شانس
            logger.debug("🖱️ تعاملات تصادفی...")
            await random_interactions(page)
        
        # 6. اسکرول نهایی
        if random.random() < 0.5:
            await scroll_page_naturally(page)
        
        # 7. توقف نهایی قبل از خروج
        final_wait = random.uniform(2, 5)
        await asyncio.sleep(final_wait)
        
        logger.info(f"✅ بازدید موفق از {url}")
        return True
        
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ Timeout در بازدید از {url}")
        return False
    except Exception as e:
        logger.error(f"❌ خطا در بازدید از {url}: {e}")
        return False


async def visit_internal_links(
    page: Page,
    current_url: str,
    target_domain: str,
    max_links: int = 3
) -> int:
    """
    بازدید از لینک‌های داخلی با رفتار طبیعی
    
    Returns:
        تعداد لینک‌هایی که با موفقیت بازدید شدند
    """
    visited_count = 0
    
    try:
        logger.info(f"🔗 استخراج لینک‌های داخلی از {current_url}...")
        
        # استخراج لینک‌های داخلی
        internal_links = await extract_internal_links(page, current_url, target_domain)
        
        if not internal_links:
            logger.debug("⚠️ هیچ لینک داخلی یافت نشد")
            return 0
        
        # انتخاب تصادفی لینک‌ها
        num_to_visit = min(max_links, len(internal_links))
        selected_links = random.sample(internal_links, num_to_visit)
        
        logger.info(f"📋 {num_to_visit} لینک داخلی انتخاب شد")
        
        for i, link in enumerate(selected_links, 1):
            # تاخیر بین بازدید لینک‌ها
            delay = random.uniform(3, 8)
            logger.debug(f"⏳ تاخیر {delay:.1f}s قبل از لینک {i}/{num_to_visit}...")
            await asyncio.sleep(delay)
            
            # بازدید از لینک
            success = await visit_page_naturally(page, link, target_domain, is_from_search=False)
            
            if success:
                visited_count += 1
                
                # شانس بازدید از لینک‌های تو در تو (عمق 2)
                if random.random() < 0.3 and i == 1:  # فقط برای اولین لینک
                    logger.debug("🔄 بررسی لینک‌های تو در تو...")
                    nested_count = await visit_internal_links(page, link, target_domain, max_links=1)
                    visited_count += nested_count
        
        logger.info(f"✅ {visited_count} لینک داخلی با موفقیت بازدید شد")
        return visited_count
        
    except Exception as e:
        logger.error(f"❌ خطا در بازدید لینک‌های داخلی: {e}")
        return visited_count


async def smart_click_and_visit(
    page: Page,
    search_results: list,
    target_domain: str,
    search_engine_url: str
) -> bool:
    """
    کلیک هوشمند روی نتایج جستجو و بازدید با رفتار انسانی
    
    Args:
        page: صفحه Playwright
        search_results: لیست نتایج جستجو
        target_domain: دامنه هدف
        search_engine_url: URL موتور جستجو
    
    Returns:
        True اگر حداقل یک بازدید موفق بود
    """
    visited_any = False
    
    try:
        for i, result in enumerate(search_results, 1):
            try:
                result_url = result.get("url", "")
                result_title = result.get("title", "بدون عنوان")
                
                # بررسی اینکه URL متعلق به دامنه هدف است
                parsed = urlparse(result_url)
                if not parsed.netloc.lower().endswith(target_domain.lower()):
                    logger.debug(f"⏭️ رد شد (دامنه غیرهدف): {result_url}")
                    continue
                
                logger.info(f"\n{'='*70}")
                logger.info(f"🎯 نتیجه {i}: {result_title[:60]}")
                logger.info(f"🔗 {result_url}")
                logger.info(f"{'='*70}")
                
                # تاخیر قبل از کلیک (رفتار انسانی: خواندن عنوان)
                await asyncio.sleep(random.uniform(1.5, 4.0))
                
                # اسکرول به المان (اگر لازم باشد)
                try:
                    selector = result.get("selector")
                    if selector:
                        element = await page.query_selector(selector)
                        if element:
                            await element.scroll_into_view_if_needed()
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                            
                            # هاور روی المان
                            await element.hover()
                            await asyncio.sleep(random.uniform(0.3, 0.8))
                            
                            # کلیک
                            await element.click()
                        else:
                            # اگر المان پیدا نشد، مستقیم برو به URL
                            await page.goto(result_url, wait_until="domcontentloaded", timeout=45000)
                    else:
                        await page.goto(result_url, wait_until="domcontentloaded", timeout=45000)
                except Exception:
                    # fallback: رفتن مستقیم به URL
                    await page.goto(result_url, wait_until="domcontentloaded", timeout=45000)
                
                # صبر برای بارگذاری
                await asyncio.sleep(random.uniform(2, 4))
                
                # بررسی اینکه به صفحه هدف رسیده‌ایم
                current_url = page.url
                if not urlparse(current_url).netloc.lower().endswith(target_domain.lower()):
                    logger.warning(f"⚠️ به صفحه هدف نرسیدیم. URL فعلی: {current_url}")
                    await page.goto(search_engine_url, timeout=30000)
                    continue
                
                # رفتار طبیعی در صفحه
                logger.info("🎭 شروع رفتار طبیعی در صفحه...")
                
                # 1. اسکرول و خواندن
                await human_reading_behavior(page, duration_seconds=random.uniform(10, 25))
                
                # 2. تعاملات تصادفی
                if random.random() < 0.8:
                    await random_interactions(page)
                
                # 3. بازدید از لینک‌های داخلی (70% شانس)
                if random.random() < 0.7:
                    internal_visited = await visit_internal_links(
                        page, 
                        current_url, 
                        target_domain, 
                        max_links=random.randint(1, 3)
                    )
                    logger.info(f"📊 {internal_visited} لینک داخلی بازدید شد")
                
                visited_any = True
                
                # بازگشت به صفحه جستجو
                logger.info("🔙 بازگشت به موتور جستجو...")
                await page.goto(search_engine_url, timeout=30000)
                await asyncio.sleep(random.uniform(2, 4))
                
                # تاخیر بین نتایج
                if i < len(search_results):
                    delay = random.uniform(5, 12)
                    logger.debug(f"⏳ تاخیر {delay:.1f}s تا نتیجه بعدی...")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"❌ خطا در پردازش نتیجه {i}: {e}")
                try:
                    await page.goto(search_engine_url, timeout=30000)
                except Exception:
                    pass
                continue
        
        return visited_any
        
    except Exception as e:
        logger.error(f"❌ خطای کلی در smart_click_and_visit: {e}")
        return visited_any