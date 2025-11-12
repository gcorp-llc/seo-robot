import os

HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'false'
DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', '60000'))
PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', '45000'))
MAX_RESULTS_TO_CHECK = int(os.getenv('MAX_RESULTS_TO_CHECK', '30'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
SAVE_SCREENSHOTS = os.getenv('SAVE_SCREENSHOTS', 'true').lower() == 'true'
SCREENSHOT_DIR = os.getenv('SCREENSHOT_DIR', 'screenshots')
CAPTCHA_MAX_WAIT = int(os.getenv('CAPTCHA_MAX_WAIT', '120'))

CUSTOM_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (Linux; Android 11)",
]

DEVICES = [
    # iPhone devices
    {
        "name": "iPhone 15 Pro",
        "device_type": "mobile",
        "brand": "Apple",
        "os": "iOS",
        "screen_size": "6.1",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
    },
    {
        "name": "iPhone 16",
        "device_type": "mobile",
        "brand": "Apple",
        "os": "iOS",
        "screen_size": "6.1",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15"
    },
    {
        "name": "iPhone 12 Pro",
        "device_type": "mobile",
        "brand": "Apple",
        "os": "iOS",
        "screen_size": "6.1",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
    },
    {
        "name": "iPhone 12",
        "device_type": "mobile",
        "brand": "Apple",
        "os": "iOS",
        "screen_size": "6.1",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
    },
    
    # Samsung Android devices
    {
        "name": "Galaxy S25 Ultra",
        "device_type": "mobile",
        "brand": "Samsung",
        "os": "Android",
        "screen_size": "6.8",
        "user_agent": "Mozilla/5.0 (Linux; Android 15; SM-S928B) AppleWebKit/537.36"
    },
    {
        "name": "Galaxy S24 Ultra",
        "device_type": "mobile",
        "brand": "Samsung",
        "os": "Android",
        "screen_size": "6.8",
        "user_agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36"
    },
    {
        "name": "Galaxy S22 Ultra",
        "device_type": "mobile",
        "brand": "Samsung",
        "os": "Android",
        "screen_size": "6.8",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36"
    },
    
    # Google Pixel devices
    {
        "name": "Pixel 9 Pro",
        "device_type": "mobile",
        "brand": "Google",
        "os": "Android",
        "screen_size": "6.3",
        "user_agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36"
    },
    {
        "name": "Pixel 8",
        "device_type": "mobile",
        "brand": "Google",
        "os": "Android",
        "screen_size": "6.2",
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36"
    },
    {
        "name": "Pixel 7",
        "device_type": "mobile",
        "brand": "Google",
        "os": "Android",
        "screen_size": "6.1",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36"
    },
    
    # Tablets
    {
        "name": "iPad Pro 12.9",
        "device_type": "tablet",
        "brand": "Apple",
        "os": "iPadOS",
        "screen_size": "12.9",
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
    },
    {
        "name": "Galaxy Tab S9",
        "device_type": "tablet",
        "brand": "Samsung",
        "os": "Android",
        "screen_size": "11.0",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-T820) AppleWebKit/537.36"
    },
]

USE_CUSTOM_USER_AGENTS = True
ENABLE_TRACING = False

SEARCH_ENGINES_ENABLED = {
    "Google": True,
    "Bing": True,
    "DuckDuckGo": True,
    "Yandex": True,
    "Yahoo": True,
    "Brave": False,
    "Ecosia": False,
    "Startpage": False
}
