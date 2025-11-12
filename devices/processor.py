import asyncio
import random

from playwright.async_api import Playwright, Browser, Page
from typing import Dict

from config.general_settings import ENABLE_TRACING
from config.proxy_config import ProxyConfig
from core.logger import logger
from crawler.search_engine import search_in_engine
from crawler.page_visit import visit_page_naturally
from crawler.link_extractor import extract_internal_links
from config.search_engines import get_search_engines
from config.human_settings import BETWEEN_ENGINES_DELAY, BETWEEN_PAGES_DELAY

async def process_device(
    playwright: Playwright,
    browser: Browser,
    device_name: str,
    proxy: Optional[ProxyConfig],
    target: Dict
) -> None:
    target_domain = target["TARGET_DOMAIN"]
    queries = target.get("QUERIES", [])
    direct_urls = target.get("DIRECT_VISIT_URLS", [])
    do_search = target.get("SEARCH", False) and queries
    do_direct_visit = bool(direct_urls)
    logger.info(f"\n{'='*80}")
    logger.info(f"📱 دستگاه: {device_name}")
    logger.info(f"🎯 هدف: {target_domain}")
    logger.info(f"🔌 پروکسی: {proxy.url if proxy else 'بدون پروکسی'}")
    logger.info(f"{'='*80}")
    device = playwright.devices.get(device_name)
    if not device:
        logger.warning(f"⚠️ دستگاه {device_name} یافت نشد")
        return
    context = await browser.new_context(
        **device,
        locale='fa-IR',
        timezone_id='Asia/Tehran',
        extra_http_headers={
            'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        }
    )
    await context.add_init_script(""" 
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['fa-IR', 'fa', 'en-US', 'en']});
        window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}};
    """)
    
    if ENABLE_TRACING:
        await context.tracing.start(name=f"trace_{device_name}", screenshots=True, snapshots=True)
    page = await context.new_page()
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