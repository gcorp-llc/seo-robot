import asyncio
import random
import sys
import inspect
from typing import List, Optional, Dict, Any

from config import TARGETS, proxy_manager, USE_PROXY_ROTATION
from config.proxy_loader import get_active_proxies_advanced
from core import logger, performance_monitor
from core.error_handler import global_error_handler
from browser.pool import get_browser_from_pool, cleanup_browser_pool
from playwright.async_api import async_playwright
from devices.processor import process_device
from config.general_settings import DEVICES

async def main():
    logger.info("="*80)
    logger.info("🚀 ربات SEO - شروع برنامه (نسخه بازدید هوشمند)")
    logger.info("="*80)
    logger.info(f"🎯 تعداد اهداف: {len(TARGETS)}")
    logger.info(f"📱 تعداد دستگاه‌ها: {len(DEVICES)}")
    logger.info("="*80)
    
    # support both sync and async implementations of get_active_proxies_advanced
    try:
        maybe_awaitable = get_active_proxies_advanced()
        if inspect.isawaitable(maybe_awaitable):
            active_proxies = await maybe_awaitable
        else:
            active_proxies = maybe_awaitable
    except Exception as e:
        logger.error(f"❌ خطا در بارگذاری پروکسی‌ها: {e}", exc_info=True)
        active_proxies = []
    
    if not active_proxies:
        logger.error("❌ هیچ پروکسی فعالی یافت نشد!")
        return
    
    # normalize active_proxies (ensure it's a list)
    if not isinstance(active_proxies, list):
        try:
            active_proxies = list(active_proxies)
        except Exception:
            active_proxies = [active_proxies]
    
    logger.info(f"🔌 تعداد پروکسی‌های فعال بارگذاری‌شده از CSV: {len(active_proxies)}")
    
    async with async_playwright() as playwright:
        semaphore = asyncio.Semaphore(3)
        
        async def process_target(target: Dict[str, Any]):
            async with semaphore:
                proxy_rotation_list = active_proxies if USE_PROXY_ROTATION else [random.choice(active_proxies)]
                
                for proxy in proxy_rotation_list:
                    # support None proxy (no-proxy option)
                    proxy_str = getattr(proxy, "url", None) or "بدون پروکسی"
                    logger.info(f"\n🔌 پروکسی: {proxy_str} (برای {target['TARGET_DOMAIN']})")
                    
                    try:
                        browser = await get_browser_from_pool(playwright, proxy)
                        
                        num_devices = random.randint(1, min(3, len(DEVICES)))
                        selected_devices = random.sample(DEVICES, num_devices)
                        
                        for device in selected_devices:
                            await process_device(playwright, browser, device, proxy, target)
                            delay = random.uniform(10, 20)
                            await asyncio.sleep(delay)
                        
                        # small delay between proxies in rotation
                        if proxy_rotation_list.index(proxy) < len(proxy_rotation_list) - 1:
                            delay = random.uniform(15, 30)
                            await asyncio.sleep(delay)
                            
                    except Exception as e:
                        logger.error(f"❌ خطا در استفاده از پروکسی {proxy_str}: {e}", exc_info=True)
                        # mark proxy failed if manager available and proxy has url
                        if proxy and getattr(proxy, "url", None):
                            try:
                                proxy_manager.mark_failed(proxy.url)
                            except Exception:
                                logger.debug("⚠️ خطا در علامت‌گذاری پروکسی به عنوان ناموفق", exc_info=True)
                        continue
        
        tasks = [process_target(target) for target in TARGETS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # log any exceptions from gather
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"❌ خطا در اجرای تسک‌ها: {r}", exc_info=True)
        
        await cleanup_browser_pool()
    
    logger.info("\n" + "="*80)
    logger.info("✅ برنامه با موفقیت به پایان رسید")
    logger.info("="*80)
    
    summary = performance_monitor.get_summary()
    logger.info("\n📊 آمار نهایی عملکرد:")
    logger.info(f"   ⏱️  زمان اجرا: {summary['runtime_minutes']:.1f} دقیقه")
    logger.info(f"   🔍 نرخ موفقیت جستجو: {summary['search_success_rate']:.1f}%")
    logger.info(f"   🌐 نرخ موفقیت بازدید: {summary['visit_success_rate']:.1f}%")
    logger.info(f"   📊 میانگین زمان جستجو: {summary['avg_search_time']:.1f} ثانیه")
    logger.info(f"   ⏰ میانگین زمان بازدید: {summary['avg_visit_time']:.1f} ثانیه")
    logger.info(f"   ❌ تعداد خطاها: {summary['total_errors']}")
    logger.info(f"   🔌 نرخ شکست پروکسی: {summary['proxy_failure_rate']:.1f}%")
    logger.info(f"   🤖 نرخ مواجهه با CAPTCHA: {summary['captcha_rate']:.1f}%")
    
    performance_monitor.save_report()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("\n⚠️ برنامه توسط کاربر متوقف شد")
    except Exception as e:
        logger.critical(f"❌ خطای بحرانی: {e}", exc_info=True)
        sys.exit(1)