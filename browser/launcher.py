from typing import Optional

from playwright.async_api import Playwright, Browser
from network.proxy_config_model import ProxyConfig
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
        '--ignore-certificate-errors',  # نادیده گرفتن خطاهای گواهی SSL
        '--ignore-ssl-errors',  # نادیده گرفتن خطاهای SSL
        '--disable-features=CertificateTransparencyEnforcement',  # غیرفعال کردن CT
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