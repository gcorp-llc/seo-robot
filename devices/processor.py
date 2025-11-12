import random
import asyncio
from urllib.parse import urlparse

from playwright.async_api import Playwright, Browser, Page
from typing import Dict, Optional

from config.general_settings import ENABLE_TRACING
from network.proxy_config_model import ProxyConfig
from core.logger import logger
from crawler.search_engine import search_in_engine
from crawler.page_visit import visit_page_naturally, visit_internal_links, smart_click_and_visit
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
    پردازش یک دستگاه با رفتار کاملاً انسانی
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
    
    # تعیین مشخصات دستگاه
    device_spec = None
    device_name = None

    if isinstance(device, dict):
        device_name = device.get("name")
        if device_name:
            try:
                device_spec = playwright.devices.get(device_name)
            except Exception:
                device_spec = None
        
        if not device_spec:
            device_spec = {
                "user_agent": device.get("user_agent"),
                "viewport": {"width": 390, "height": 844} if device.get("device_type") == "mobile" else {"width": 1280, "height": 800},
                "is_mobile": device.get("device_type") == "mobile",
                "device_scale_factor": float(device.get("device_scale_factor", 2))
            }
    elif isinstance(device, str):
        device_name = device
        try:
            device_spec = playwright.devices.get(device_name)
        except Exception:
            device_spec = None

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
            except Exception:
                pass
    
    if device_name:
        logger.info(f"📱 دستگاه انتخاب‌شده: {device_name}")
    else:
        logger.info(f"📱 دستگاه انتخاب‌شده (مخصص): {device}")

    # ساخت context
    context_kwargs = {"ignore_https_errors": True}
    if device_spec:
        ua = device_spec.get("userAgent") or device_spec.get("user_agent")
        if ua:
            context_kwargs["user_agent"] = ua
        viewport = device_spec.get("viewport")
        if viewport:
            context_kwargs["viewport"] = viewport
        is_mobile = device_spec.get("isMobile") if "isMobile" in device_spec else device_spec.get("is_mobile")
        if is_mobile is not None:
            context_kwargs["is_mobile"] = bool(is_mobile)
        if "device_scale_factor" in device_spec:
            context_kwargs["device_scale_factor"] = device_spec.get("device_scale_factor")

    try:
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        
        if ENABLE_TRACING:
            await context.tracing.start(name=f"trace_{device_name}", screenshots=True, snapshots=True)
        
        try:
            # ═══════════════════════════════════════════════════════════
            # بخش 1: جستجو و بازدید از نتایج با رفتار انسانی
            # ═══════════════════════════════════════════════════════════
            if do_search:
                logger.info("\n" + "="*80)
                logger.info("🔍 حالت: جستجو و بازدید هوشمند")
                logger.info("="*80)
                
                for query in queries:
                    logger.info(f"\n🔎 کوئری: {query}")
                    active_engines = [e for e in get_search_engines(query) if e.get("enabled", True)]
                    
                    if not active_engines:
                        logger.warning("⚠️ هیچ موتور جستجوی فعالی یافت نشد")
                        continue
                    
                    logger.info(f"موتورهای فعال: {[e['name'] for e in active_engines]}")
                    
                    for engine in active_engines:
                        logger.info(f"\n{'='*70}")
                        logger.info(f"🔎 موتور: {engine['name']}")
                        logger.info(f"{'='*70}")
                        
                        # جستجو در موتور
                        results = await search_in_engine(page, engine)
                        
                        if not results:
                            logger.warning(f"⚠️ هیچ نتیجه‌ای در {engine['name']} یافت نشد")
                            continue
                        
                        logger.info(f"✅ {len(results)} نتیجه یافت شد")
                        
                        # کلیک و بازدید هوشمند با رفتار انسانی
                        visited = await smart_click_and_visit(
                            page, 
                            results, 
                            target_domain, 
                            engine["url"]
                        )
                        
                        if visited:
                            logger.info(f"✅ بازدید موفق از نتایج {engine['name']}")
                        else:
                            logger.warning(f"⚠️ هیچ بازدید موفقی از {engine['name']} انجام نشد")
                        
                        # تاخیر بین موتورها
                        if active_engines.index(engine) < len(active_engines) - 1:
                            delay = random.uniform(*BETWEEN_ENGINES_DELAY)
                            logger.info(f"\n⏳ تاخیر {delay:.1f}s تا موتور بعدی...")
                            await asyncio.sleep(delay)
            
            # ═══════════════════════════════════════════════════════════
            # بخش 2: بازدید مستقیم از URLها با رفتار انسانی
            # ═══════════════════════════════════════════════════════════
            if do_direct_visit:
                logger.info("\n" + "="*80)
                logger.info("🎯 حالت: بازدید مستقیم")
                logger.info("="*80)
                
                # انتخاب تصادفی از URLها
                num_to_visit = min(3, len(direct_urls))
                selected_urls = random.sample(direct_urls, num_to_visit)
                
                logger.info(f"📋 {num_to_visit} URL برای بازدید انتخاب شد")
                
                for i, direct_url in enumerate(selected_urls, 1):
                    logger.info(f"\n{'─'*70}")
                    logger.info(f"🌐 URL {i}/{num_to_visit}: {direct_url}")
                    logger.info(f"{'─'*70}")
                    
                    # تاخیر بین صفحات
                    if i > 1:
                        delay = random.uniform(*BETWEEN_PAGES_DELAY)
                        logger.info(f"⏳ تاخیر {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    
                    # بازدید طبیعی از صفحه
                    success = await visit_page_naturally(
                        page, 
                        direct_url, 
                        target_domain, 
                        is_from_search=False
                    )
                    
                    if not success:
                        logger.warning(f"⚠️ بازدید از {direct_url} ناموفق بود")
                        continue
                    
                    # بازدید از لینک‌های داخلی (70% شانس)
                    if random.random() < 0.7:
                        logger.info("\n🔗 شروع بازدید از لینک‌های داخلی...")
                        
                        num_internal = random.randint(1, 3)
                        internal_visited = await visit_internal_links(
                            page,
                            direct_url,
                            target_domain,
                            max_links=num_internal
                        )
                        
                        logger.info(f"📊 {internal_visited} لینک داخلی بازدید شد")
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ پردازش {device_name} برای {target_domain} کامل شد")
            logger.info(f"{'='*80}")
            
        except Exception as e:
            logger.error(f"❌ خطای کلی در {device_name} برای {target_domain}: {e}", exc_info=True)
            
        finally:
            if ENABLE_TRACING:
                await context.tracing.stop(path=f"logs/trace_{target_domain}_{device_name}.zip")
            
            await context.close()
            await asyncio.sleep(random.uniform(2, 4))
            
    except Exception as e:
        logger.error(f"❌ خطا در پردازش دستگاه {device_name or device}: {e}", exc_info=True)
        raise