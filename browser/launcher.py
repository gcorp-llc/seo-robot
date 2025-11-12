from typing import Optional

from playwright.async_api import Playwright, Browser
from config.proxy_config import ProxyConfig
from config.general_settings import HEADLESS

async def launch_browser_with_proxy(playwright: Playwright, proxy_config: Optional[ProxyConfig] = None) -> Browser:
    browser_args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-site-isolation-trials',
        '--disable-web-security',
        '--disable-features=BlockInsecurePrivateNetworkRequests',
        '--disable-features=OutOfBlinkCors',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu',
    ]
    
    proxy_dict = None
    if proxy_config:
        proxy_dict = {
            "server": proxy_config.url,
        }
        if hasattr(proxy_config, 'username') and proxy_config.username:
            proxy_dict["username"] = proxy_config.username
        if hasattr(proxy_config, 'password') and proxy_config.password:
            proxy_dict["password"] = proxy_config.password
    
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=browser_args,
        proxy=proxy_dict,
        ignore_default_args=["--enable-automation"],
    )
    
    return browser