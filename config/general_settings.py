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
    "iPhone 15 Pro",
    "iPhone 16",
    "iPhone 12 Pro",
    "iPhone 12",
    "Pixel 7",
    "Galaxy S22 Ultra",
    "Galaxy S24 Ultra",
    "Galaxy S25"
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
