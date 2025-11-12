# -*- coding: utf-8 -*-
import asyncio
import random
import sys
from typing import Dict, Any

# --- ایمپورت‌های اصلی ---
from config.targets import TARGETS
from config import USE_PROXY_ROTATION
from config.proxy_config import MANUAL_PROXIES
from network.proxy_manager import proxy_manager
from network.proxy_checker import run_proxy_validation

from core import logger, performance_monitor
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
    
    logger.info("... در حال بارگذاری پروکسی‌ها ...")
    try:
        # ✅ اضافه کردن فقط MANUAL_PROXIES
        if MANUAL_PROXIES:
            added = proxy_manager.add_manual_proxies(MANUAL_PROXIES)
            logger.info(f"✅ {added} پروکسی دستی اضافه شد")
        else:
            logger.warning("⚠️ هیچ پروکسی دستی تعریف نشده!")
            return

        # بررسی پروکسی‌ها
        logger.info("در حال بررسی پروکسی‌ها...")
        await run_proxy_validation()
        
        # دریافت پروکسی‌های معتبر
        active_proxies = proxy_manager.get_active_proxies()
        
    except Exception as e:
        logger.error(f"❌ خطا: {e}", exc_info=True)
        active_proxies = []
    
    if not active_proxies:
        logger.error("❌ هیچ پروکسی معتبری یافت نشد!")
        return

    logger.info(f"🔌 {len(active_proxies)} پروکسی فعال")
    
    async with async_playwright() as playwright:
        # محدودیت همزمانی برای تسک‌های اصلی (پردازش اهداف)
        # شما این را 3 گذاشته بودید، من آن را حفظ می‌کنم
        semaphore = asyncio.Semaphore(3)
        
        async def process_target(target: Dict[str, Any]):
            async with semaphore:
                # انتخاب پروکسی‌ها برای چرخش
                proxy_rotation_list = active_proxies if USE_PROXY_ROTATION else [random.choice(active_proxies)]
                
                for proxy in proxy_rotation_list:
                    # پشتیبانی از 'None' اگر آن را دستی اضافه کرده باشید
                    proxy_str = getattr(proxy, "url", None) or "بدون پروکسی"
                    logger.info(f"\n🔌 پروکسی: {proxy_str} (برای {target['TARGET_DOMAIN']})")
                    
                    try:
                        browser = await get_browser_from_pool(playwright, proxy)
                        
                        num_devices = random.randint(1, min(3, len(DEVICES)))
                        selected_devices = random.sample(DEVICES, num_devices)
                        
                        for device in selected_devices:
                            # اگر device یک dict باشد نام آن را استخراج کن، در غیر این صورت فرض کن رشته است
                            if isinstance(device, dict):
                                device_name = device.get("name") or str(device)
                            else:
                                device_name = str(device)
                            
                            logger.info(f"📱 دستگاه انتخاب‌شده: {device_name}")
                            
                            # ارسال نام دستگاه به process_device (رعایت backward-compatibility)
                            await process_device(playwright, browser, device_name, proxy, target)
                            delay = random.uniform(10, 20)
                            await asyncio.sleep(delay)
                        
                        # تاخیر کوتاه بین پروکسی‌ها در چرخش
                        if proxy_rotation_list.index(proxy) < len(proxy_rotation_list) - 1:
                            delay = random.uniform(15, 30)
                            await asyncio.sleep(delay)
                            
                    except Exception as e:
                        logger.error(f"❌ خطا در استفاده از پروکسی {proxy_str}: {e}", exc_info=True)
                        
                        # --- (مهم) اصلاح نحوه علامت‌گذاری خطا ---
                        # اگر پروکسی آبجکت معتبر 'ProxyConfig' باشد
                        if proxy and hasattr(proxy, 'mark_failed'):
                            try:
                                # به جای proxy_manager.mark_failed()...
                                proxy.mark_failed()
                                logger.warning(f"⚠️ پروکسی {proxy_str} به عنوان ناموفق علامت‌گذاری شد.")
                            except Exception as mark_e:
                                logger.debug(f"⚠️ خطا در علامت‌گذاری پروکسی: {mark_e}", exc_info=True)
                        continue
        
        tasks = [process_target(target) for target in TARGETS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # لاگ کردن هر خطایی که از gather برمی‌گردد
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"❌ خطا در اجرای تسک اصلی: {r}", exc_info=True)
        
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