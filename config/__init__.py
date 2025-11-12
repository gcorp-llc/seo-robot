from .main_config import *
from .proxy_config import ProxyType, ProxyConfig, ProxyManager, proxy_manager
from .search_engines import get_search_engines, SEARCH_ENGINES_ENABLED
from .targets import TARGETS, is_same_domain, human_delay
from .human_settings import HUMAN_DELAY_RANGE, INTERACTION_DELAY_RANGE, SCROLL_DELAY_RANGE, BETWEEN_ENGINES_DELAY, BETWEEN_PAGES_DELAY, STAY_ON_PAGE_RANGE, HUMAN_BEHAVIOR, MOUSE_MOVEMENTS_RANGE, CLICK_CHANCE, BACK_TO_TOP_CHANCE, RANDOMNESS_FACTOR
from .general_settings import HEADLESS, DEFAULT_TIMEOUT, PAGE_LOAD_TIMEOUT, MAX_RESULTS_TO_CHECK, LOG_LEVEL, SAVE_SCREENSHOTS, SCREENSHOT_DIR, CAPTCHA_MAX_WAIT, CUSTOM_USER_AGENTS, DEVICES, USE_CUSTOM_USER_AGENTS, ENABLE_TRACING
from .crawler_settings import MODES, DEEP_CRAWL_MAX_LINKS, DEEP_CRAWL_MAX_DEPTH, get_deep_crawl_selectors, FALLBACK_STRATEGIES, MAX_SCROLL_ROUNDS, PAGE_SCROLL_PASSES
from .proxy_loader import load_proxies_from_csv_advanced, PROXY_CONFIG, PROXY_SECURITY, USE_PROXY_ROTATION, INCLUDE_NO_PROXY, MAX_RETRIES_PER_PROXY, PROXY_CHECK_TIMEOUT

# محاسبه PROXIES و ACTIVE_PROXIES پس از importها
PROXIES = proxy_manager.get_all_proxy_urls()
ACTIVE_PROXIES = proxy_manager.get_active_proxy_urls()