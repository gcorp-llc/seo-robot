import time
import asyncio
import aiohttp
import random

from config.proxy_config import ProxyConfig
from config.general_settings import CUSTOM_USER_AGENTS
from config.proxy_loader import PROXY_CHECK_TIMEOUT, proxy_manager
from core.performance_monitor import performance_monitor
from core.logger import logger

_proxy_check_cache = {}
_proxy_check_cache_timeout = 300  # 5 دقیقه

async def check_proxy_advanced(proxy_config: ProxyConfig) -> bool:
    current_time = time.time()
    cache_key = proxy_config.url
    
    if cache_key in _proxy_check_cache:
        cached_result, cache_time = _proxy_check_cache[cache_key]
        if current_time - cache_time < _proxy_check_cache_timeout:
            logger.debug(f"📋 استفاده از کش برای پروکسی: {proxy_config.url}")
            return cached_result
    
    try:
        timeout = aiohttp.ClientTimeout(total=PROXY_CHECK_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "https://httpbin.org/ip", 
                proxy=proxy_config.url,
                headers={'User-Agent': random.choice(CUSTOM_USER_AGENTS)}
            ) as resp:
                success = resp.status == 200
                if success:
                    proxy_manager.mark_success(proxy_config.url)
                    data = await resp.json()
                    logger.debug(f"✅ پروکسی {proxy_config.url} فعال است - IP: {data.get('origin', 'Unknown')}")
                else:
                    proxy_manager.mark_failed(proxy_config.url)
                    logger.warning(f"⚠️ پروکسی {proxy_config.url} پاسخ ناموفق: {resp.status}")
                _proxy_check_cache[cache_key] = (success, current_time)
                return success
    except asyncio.TimeoutError:
        logger.warning(f"⏰ تایم‌اوت در بررسی پروکسی {proxy_config.url}")
        proxy_manager.mark_failed(proxy_config.url)
        performance_monitor.record_proxy_failure()
        result = False
    except Exception as e:
        logger.debug(f"❌ پروکسی {proxy_config.url} فعال نیست: {str(e)[:100]}")
        proxy_manager.mark_failed(proxy_config.url)
        performance_monitor.record_proxy_failure()
        result = False
    
    _proxy_check_cache[cache_key] = (result, current_time)
    return result

async def get_active_proxies_advanced() -> List[Optional[ProxyConfig]]:
    logger.info("🔍 در حال بررسی پیشرفته پروکسی‌ها...")
    
    if not proxy_manager:
        logger.warning("⚠️ مدیر پروکسی در دسترس نیست")
        return [None] if INCLUDE_NO_PROXY else []
    
    active_proxies = []
    
    if proxy_manager.active_proxies:
        logger.info(f"📊 در حال بررسی {len(proxy_manager.active_proxies)} پروکسی فعال...")
        
        semaphore = asyncio.Semaphore(10)
        
        async def check_with_semaphore(proxy_config):
            async with semaphore:
                return await check_proxy_advanced(proxy_config)
        
        checks = await asyncio.gather(*[check_with_semaphore(p) for p in proxy_manager.active_proxies])
        
        active_proxies = [p for p, is_active in zip(proxy_manager.active_proxies, checks) if is_active]
    
    if INCLUDE_NO_PROXY:
        active_proxies.append(None)
    
    return active_proxies