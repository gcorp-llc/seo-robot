from typing import Optional
from datetime import datetime

from playwright.async_api import Playwright, Browser
from config.proxy_config import ProxyConfig
from core.logger import logger
from .launcher import launch_browser_with_proxy

_browser_pool = {}
_browser_pool_max_size = 3

async def get_browser_from_pool(playwright: Playwright, proxy_config: Optional[ProxyConfig] = None) -> Browser:
    global _browser_pool
    
    proxy_key = proxy_config.url if proxy_config else "no_proxy"
    
    if proxy_key in _browser_pool:
        browser_info = _browser_pool[proxy_key]
        try:
            if browser_info['browser'].is_connected():
                logger.debug(f"📋 استفاده مجدد از مرورگر برای پروکسی: {proxy_key}")
                return browser_info['browser']
            else:
                del _browser_pool[proxy_key]
        except Exception:
            del _browser_pool[proxy_key]
    
    browser = await launch_browser_with_proxy(playwright, proxy_config)
    
    if len(_browser_pool) < _browser_pool_max_size:
        _browser_pool[proxy_key] = {
            'browser': browser,
            'created_at': datetime.now()
        }
    
    return browser

async def cleanup_browser_pool():
    global _browser_pool
    for proxy_key, browser_info in list(_browser_pool.items()):
        try:
            await browser_info['browser'].close()
        except Exception:
            pass
    _browser_pool.clear()