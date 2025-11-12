import asyncio
import random

from playwright.async_api import Playwright, Browser, Page
from typing import Dict, Optional

from config.general_settings import ENABLE_TRACING
from network.proxy_config_model import ProxyConfig
from core.logger import logger
from crawler.search_engine import search_in_engine
from crawler.page_visit import visit_page_naturally
from crawler.link_extractor import extract_internal_links
from config.search_engines import get_search_engines
from config.human_settings import BETWEEN_ENGINES_DELAY, BETWEEN_PAGES_DELAY

async def process_device(
    playwright: Playwright,
    browser: Browser,
    device: str,
    proxy: Optional[ProxyConfig],
    target: Dict
) -> None:
    """
    پردازش یک دستگاه: device می‌تواند:
    - نام دستگاه (string) که در playwright.devices باشد
    - یا یک dict از DEVICES در config.general_settings
    """
    target_domain = target["TARGET_DOMAIN"]
    queries = target.get("QUERIES", [])
    direct_urls = target.get("DIRECT_VISIT_URLS", [])
    do_search = target.get("SEARCH", False) and queries
    do_direct_visit = bool(direct_urls)
    logger.info(f"\n{'='*80}")
    logger.info(f"📱 دستگاه: {device}")
    logger.info(f"🎯 هدف: {target_domain}")
    logger.info(f"🔌 پروکسی: {proxy.url if proxy else 'بدون پروکسی'}")
    logger.info(f"{'='*80}")
    
    # تعیین مشخصات دستگاه به صورت مقاوم
    device_spec = None
    device_name = None

    # اگر ورودی یک dict است، تلاش کن نام را بگیری و از مقادیرش استفاده کنی
    if isinstance(device, dict):
        device_name = device.get("name")
        # تلاش برای گرفتن مشخصات از playwright (اگر نام متناظر وجود داشته باشد)
        if device_name:
            try:
                device_spec = playwright.devices.get(device_name)
            except Exception:
                device_spec = None
        # اگر playwright مشخصاتی نداشت، تبدیل از dict محلی
        if not device_spec:
            device_spec = {
                "user_agent": device.get("user_agent"),
                "viewport": {"width": 390, "height": 844} if device.get("device_type") == "mobile" else {"width": 1280, "height": 800},
                "is_mobile": device.get("device_type") == "mobile",
                "device_scale_factor": float(device.get("device_scale_factor", 2))
            }
    elif isinstance(device, str):
        # رشته: نام دستگاه؛ اول تلاش کن از playwright.devices بگیری
        device_name = device
        try:
            device_spec = playwright.devices.get(device_name)
        except Exception:
            device_spec = None

        # اگر پیدا نشد، جستجو در کانفیگ DEVICES
        if not device_spec:
            try:
                from config.general_settings import DEVICES as CFG_DEVICES
                found = next((d for d in CFG_DEVICES if d.get("name") == device_name), None)
                if found:
                    device_spec = {
                        "user_agent": found.get("user_agent"),
                        "viewport": {"width": 390, "height": 844} if found.get("device_type") == "mobile" else {"width": 1280, "height": 800},
                        "is_mobile": found.get("device_type") == "mobile",
                        "device_scale_factor": float(found.get("device_scale_factor", 2))
                    }
                else:
                    device_spec = None
            except Exception:
                device_spec = None
    else:
        # هر نوع دیگر: fallback به پیش‌فرض
        device_spec = None

    # لاگ وضعیت دستگاه
    if device_name:
        logger.info(f"📱 دستگاه انتخاب‌شده: {device_name}")
    else:
        logger.info(f"📱 دستگاه انتخاب‌شده (مخصّص نشده): {device}")

    # ساخت context بر اساس device_spec یا پیش‌فرض
    context_kwargs = {"ignore_https_errors": True}
    if device_spec:
        # اگر device_spec از playwright بود، حاوی کلیدهایی مانند userAgent, viewport و غیره است
        ua = device_spec.get("userAgent") or device_spec.get("user_agent")
        if ua:
            context_kwargs["user_agent"] = ua
        viewport = device_spec.get("viewport")
        if viewport:
            context_kwargs["viewport"] = viewport
        # playwright uses 'is_mobile' key
        is_mobile = device_spec.get("isMobile") if "isMobile" in device_spec else device_spec.get("is_mobile")
        if is_mobile is not None:
            context_kwargs["is_mobile"] = bool(is_mobile)
        if "device_scale_factor" in device_spec:
            context_kwargs["device_scale_factor"] = device_spec.get("device_scale_factor")

    # اگر browser از قبل با پروکسی لانچ شده است، نیازی به proxy در context نیست.
    # ساخت context و صفحه
    try:
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        if ENABLE_TRACING:
            await context.tracing.start(name=f"trace_{device_name}", screenshots=True, snapshots=True)
        try:
            if do_search:
                logger.info("\n🔍 حالت: جستجو و بازدید هوشمند")
                for query in queries:
                    logger.info(f"\n   🔎 کوئری: {query}")
                    active_engines = [e for e in get_search_engines(query) if e.get("enabled", True)]
                    if not active_engines:
                        continue
                    logger.info(f"   موتورهای فعال: {[e['name'] for e in active_engines]}")
                    for engine in active_engines:
                        logger.info(f"\n{'='*70}")
                        logger.info(f"🔎 موتور: {engine['name']}")
                        logger.info(f"{'='*70}")
                        results = await search_in_engine(page, engine)
                        if not results:
                            continue
                        from crawler.page_visit import smart_click_and_visit
                        await smart_click_and_visit(page, results, target_domain, engine["url"])
                        delay = random.uniform(*BETWEEN_ENGINES_DELAY)
                        logger.info(f"\n⏳ تاخیر {delay:.1f}s تا موتور بعدی...")
                        await asyncio.sleep(delay)
            if do_direct_visit:
                logger.info("\n🎯 حالت: بازدید مستقیم")
                num_to_visit = min(3, len(direct_urls))
                selected_urls = random.sample(direct_urls, num_to_visit)
                for direct_url in selected_urls:
                    await asyncio.sleep(random.uniform(*BETWEEN_PAGES_DELAY))
                    success = await visit_page_naturally(page, direct_url, target_domain, is_from_search=False)
                    if success and random.random() < 0.7:
                        internal_links = await extract_internal_links(page, direct_url, target_domain)
                        if internal_links:
                            num_internal = min(2, len(internal_links))
                            selected_internal = random.sample(internal_links, num_internal)
                            logger.info(f"\n🔗 بازدید {num_internal} لینک داخلی...")
                            for internal_url in selected_internal:
                                await asyncio.sleep(random.uniform(5, 10))
                                await visit_page_naturally(page, internal_url, target_domain, is_from_search=False)
            logger.info(f"\n✅ پردازش {device_name} برای {target_domain} کامل شد")
        except Exception as e:
            logger.error(f"❌ خطای کلی در {device_name} برای {target_domain}: {e}", exc_info=True)
        finally:
            if ENABLE_TRACING:
                await context.tracing.stop(path=f"logs/trace_{target_domain}_{device_name}.zip")  # انتقال به logs
            await context.close()
            await asyncio.sleep(random.uniform(2, 4))
    except Exception as e:
        logger.error(f"❌ خطا در پردازش دستگاه {device_name or device}: {e}", exc_info=True)
        # در صورت خطا، بازگشت تا caller بتواند پروکسی را علامت‌گذاری کند یا ادامه دهد
        raise