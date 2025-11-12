import asyncio
import random
import logging
import sys
import re
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin, quote_plus
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Set, Any
from functools import lru_cache
import hashlib
from logging.handlers import RotatingFileHandler
from enum import Enum
from dataclasses import dataclass

import aiohttp
from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    BrowserContext,
    Playwright,
    TimeoutError as PlaywrightTimeout,
    Route,
)

# Import settings
import config

# Logging setup with rotating logs
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class RotatingFileHandlerSafe(RotatingFileHandler):
    """RotatingFileHandler با پشتیبانی از رمزنگاری UTF-8 و مدیریت خطا"""
    def __init__(self, filename, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'):
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount, encoding=encoding)
    
    def emit(self, record):
        try:
            super().emit(record)
        except Exception as e:
            print(f"خطا در لاگینگ: {e}")

# ==================== Performance Monitoring ====================

class PerformanceMonitor:
    """سیستم مانیتورینگ عملکرد و آمار"""
    
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'total_visits': 0,
            'successful_visits': 0,
            'failed_visits': 0,
            'proxy_failures': 0,
            'captcha_encounters': 0,
            'start_time': datetime.now(),
            'errors': []
        }
        self.search_times = []
        self.visit_times = []
    
    def record_search(self, success: bool, duration: float = None):
        self.stats['total_searches'] += 1
        if success:
            self.stats['successful_searches'] += 1
            if duration:
                self.search_times.append(duration)
        else:
            self.stats['failed_searches'] += 1
    
    def record_visit(self, success: bool, duration: float = None):
        self.stats['total_visits'] += 1
        if success:
            self.stats['successful_visits'] += 1
            if duration:
                self.visit_times.append(duration)
        else:
            self.stats['failed_visits'] += 1
    
    def record_proxy_failure(self):
        self.stats['proxy_failures'] += 1
    
    def record_captcha(self):
        self.stats['captcha_encounters'] += 1
    
    def record_error(self, error: str):
        self.stats['errors'].append({
            'timestamp': datetime.now(),
            'error': error
        })
    
    def get_summary(self) -> dict:
        runtime = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        avg_search_time = sum(self.search_times) / len(self.search_times) if self.search_times else 0
        avg_visit_time = sum(self.visit_times) / len(self.visit_times) if self.visit_times else 0
        
        return {
            'runtime_minutes': runtime,
            'search_success_rate': (self.stats['successful_searches'] / max(self.stats['total_searches'], 1)) * 100,
            'visit_success_rate': (self.stats['successful_visits'] / max(self.stats['total_visits'], 1)) * 100,
            'avg_search_time': avg_search_time,
            'avg_visit_time': avg_visit_time,
            'total_errors': len(self.stats['errors']),
            'proxy_failure_rate': (self.stats['proxy_failures'] / max(self.stats['total_searches'], 1)) * 100,
            'captcha_rate': (self.stats['captcha_encounters'] / max(self.stats['total_searches'], 1)) * 100
        }
    
    def save_report(self, filename: str = None):
        if not filename:
            filename = f"performance_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        report = {
            'statistics': self.stats,
            'summary': self.get_summary(),
            'search_times': self.search_times,
            'visit_times': self.visit_times
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"📊 گزارش عملکرد ذخیره شد: {filename}")
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره گزارش عملکرد: {e}")

# ایجاد نمونه جهانی مانیتور
performance_monitor = PerformanceMonitor()

# ==================== Advanced Error Handling ====================

class ErrorType(Enum):
    """انواع خطاها برای مدیریت بهتر"""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    CAPTCHA_ERROR = "captcha_error"
    PROXY_ERROR = "proxy_error"
    BROWSER_ERROR = "browser_error"
    PAGE_ERROR = "page_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class ErrorContext:
    """اطلاعات زمینه خطا برای لاگینگ و اشکال‌زدایی"""
    error_type: ErrorType
    message: str
    function_name: str
    target_domain: str = None
    proxy: str = None
    device: str = None
    search_engine: str = None
    url: str = None
    retry_count: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class ErrorHandler:
    """مدیریت خطا با retry و fallback"""
    
    def __init__(self):
        self.retry_config = {
            ErrorType.NETWORK_ERROR: {'max_retries': 3, 'base_delay': 2},
            ErrorType.TIMEOUT_ERROR: {'max_retries': 2, 'base_delay': 5},
            ErrorType.CAPTCHA_ERROR: {'max_retries': 1, 'base_delay': 10},
            ErrorType.PROXY_ERROR: {'max_retries': 2, 'base_delay': 3},
            ErrorType.BROWSER_ERROR: {'max_retries': 2, 'base_delay': 1},
            ErrorType.PAGE_ERROR: {'max_retries': 2, 'base_delay': 2},
            ErrorType.UNKNOWN_ERROR: {'max_retries': 1, 'base_delay': 1}
        }
    
    def classify_error(self, error: Exception, context: dict = None) -> ErrorType:
        """طبقه‌بندی خطا بر اساس نوع exception"""
        error_str = str(error).lower()
        
        if isinstance(error, asyncio.TimeoutError) or 'timeout' in error_str:
            return ErrorType.TIMEOUT_ERROR
        elif isinstance(error, aiohttp.ClientError) or 'connection' in error_str:
            return ErrorType.NETWORK_ERROR
        elif 'captcha' in error_str or 'robot' in error_str:
            return ErrorType.CAPTCHA_ERROR
        elif 'proxy' in error_str:
            return ErrorType.PROXY_ERROR
        elif isinstance(error, PlaywrightTimeout) or 'playwright' in str(type(error)).lower():
            return ErrorType.BROWSER_ERROR
        elif 'page' in error_str or 'navigation' in error_str:
            return ErrorType.PAGE_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """اجرای تابع با retry و مدیریت خطا"""
        context = kwargs.pop('error_context', {})
        
        for attempt in range(config.MAX_RETRIES_PER_PROXY):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"✅ موفق در تلاش {attempt + 1} برای {context.get('function_name', func.__name__)}")
                return result
                
            except Exception as e:
                error_type = self.classify_error(e, context)
                retry_config = self.retry_config.get(error_type, {'max_retries': 1, 'base_delay': 1})
                
                error_context = ErrorContext(
                    error_type=error_type,
                    message=str(e),
                    function_name=func.__name__,
                    retry_count=attempt + 1,
                    **context
                )
                
                if attempt < retry_config['max_retries'] - 1:
                    delay = retry_config['base_delay'] * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"⚠️ تلاش {attempt + 1} ناموفق برای {func.__name__}. خطا: {e}. تلاش مجدد پس از {delay:.1f} ثانیه...")
                    
                    performance_monitor.record_error(f"{error_type.value}: {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ تمام تلاش‌ها برای {func.__name__} ناموفق بود. آخرین خطا: {e}")
                    self.log_error(error_context)
                    performance_monitor.record_error(f"{error_type.value}: {str(e)}")
                    raise
        
        return None
    
    def log_error(self, context: ErrorContext):
        """لاگ کردن اطلاعات خطا برای تحلیل"""
        error_log = {
            'timestamp': context.timestamp.isoformat(),
            'error_type': context.error_type.value,
            'function': context.function_name,
            'message': context.message,
            'retry_count': context.retry_count,
            'target_domain': context.target_domain,
            'proxy': context.proxy,
            'device': context.device,
            'search_engine': context.search_engine,
            'url': context.url
        }
        
        logger.error(f"📊 خطای ثبت شده: {json.dumps(error_log, ensure_ascii=False)}")

# ایجاد نمونه جهانی مدیریت خطا
global_error_handler = ErrorHandler()

# تنظیمات لاگ با rotating file handler
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

# ایجاد formatter برای لاگ‌ها
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# لاگ اصلی با rotating file handler
main_handler = RotatingFileHandlerSafe(
    filename=os.path.join(log_dir, 'seo_bot.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
main_handler.setFormatter(formatter)

# لاگ برای خطاها
error_log_handler = RotatingFileHandlerSafe(
    filename=os.path.join(log_dir, 'seo_bot_errors.log'),
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3
)
error_log_handler.setLevel(logging.ERROR)
error_log_handler.setFormatter(formatter)

# لاگ برای دیباگ
debug_handler = RotatingFileHandlerSafe(
    filename=os.path.join(log_dir, 'seo_bot_debug.log'),
    maxBytes=20*1024*1024,  # 20MB
    backupCount=2
)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(formatter)

# لاگ برای اطلاعات عملکرد
performance_handler = RotatingFileHandlerSafe(
    filename=os.path.join(log_dir, 'seo_bot_performance.log'),
    maxBytes=15*1024*1024,  # 15MB
    backupCount=4
)
performance_handler.setLevel(logging.INFO)
performance_handler.setFormatter(formatter)

# تنظیمات لاگ اصلی
logger = logging.getLogger('SEOBot')
logger.setLevel(getattr(logging, config.LOG_LEVEL))

# حذف handlerهای قبلی
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# اضافه کردن handlerهای جدید
logger.addHandler(main_handler)
logger.addHandler(error_log_handler)
logger.addHandler(debug_handler)
logger.addHandler(performance_handler)
logger.addHandler(logging.StreamHandler())

# تنظیم لاگ برای ماژولهای دیگر
logging.getLogger('playwright').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

logger.info(f"✅ سیستم لاگ‌ با rotating file handler راه‌اندازی شد")

# Screenshot directory
if config.SAVE_SCREENSHOTS:
    SCREENSHOT_DIR = Path(config.SCREENSHOT_DIR)
    SCREENSHOT_DIR.mkdir(exist_ok=True)

# ==================== Helper Functions ====================

def human_delay(
    a: float = None,
    b: float = None,
    randomness: float = config.RANDOMNESS_FACTOR
) -> float:
    if a is None or b is None:
        a, b = config.HUMAN_DELAY_RANGE
    base_delay = random.uniform(a, b)
    variance = base_delay * randomness * random.uniform(-1, 1)
    return max(0.5, base_delay + variance)


def is_same_domain(url: str, domain: str) -> bool:
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().replace("www.", "")
        target = domain.lower().replace("www.", "")
        return netloc == target or netloc.endswith(f".{target}")
    except Exception:
        return False


def is_valid_url(url: str, exclude_domains: List[str] = None) -> bool:
    if not url or not url.startswith("http"):
        return False
    if exclude_domains:
        for domain in exclude_domains:
            if domain in url.lower():
                return False
    return True

# ==================== Fallback Functions ====================

async def extract_urls_from_text(page: Page, exclude_domains: List[str]) -> List[str]:
    try:
        page_text = await page.inner_text('body')
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w .-]*/?'
        found_urls = re.findall(url_pattern, page_text)
        valid_urls = [u for u in found_urls if is_valid_url(u, exclude_domains)]
        logger.debug(f"   استخراج {len(valid_urls)} URL از متن صفحه")
        return list(set(valid_urls))[:20]
    except Exception as e:
        logger.error(f"   خطا در استخراج URL از متن: {e}")
        return []

async def extract_urls_from_meta(page: Page, exclude_domains: List[str]) -> List[str]:
    urls = []
    try:
        metas = await page.locator('meta[property="og:url"], meta[name="twitter:url"]').all()
        for meta in metas:
            content = await meta.get_attribute('content')
            if content and is_valid_url(content, exclude_domains):
                urls.append(content)
        logger.debug(f"   استخراج {len(urls)} URL از متا")
    except Exception as e:
        logger.error(f"   خطا در متا: {e}")
    return list(set(urls))[:10]

async def extract_urls_from_scripts(page: Page, exclude_domains: List[str]) -> List[str]:
    urls = []
    try:
        scripts = await page.locator('script').all()
        for script in scripts:
            content = await script.inner_text()
            matches = re.findall(r'https?://[^"\']+', content)
            urls.extend([u for u in matches if is_valid_url(u, exclude_domains)])
        logger.debug(f"   استخراج {len(urls)} URL از اسکریپت‌ها")
    except Exception as e:
        logger.error(f"   خطا در اسکریپت‌ها: {e}")
    return list(set(urls))[:10]

async def extract_urls_from_images(page: Page, exclude_domains: List[str]) -> List[str]:
    urls = []
    try:
        images = await page.locator('img').all()
        for img in images:
            src = await img.get_attribute('src')
            alt = await img.get_attribute('alt')
            if src and is_valid_url(src, exclude_domains):
                urls.append(src)
            if alt and re.match(r'https?://', alt):
                urls.append(alt)
        logger.debug(f"   استخراج {len(urls)} URL از تصاویر")
    except Exception as e:
        logger.error(f"   خطا در تصاویر: {e}")
    return list(set(urls))[:10]

# ==================== Proxy Management ====================

_proxy_check_cache = {}
_proxy_check_cache_timeout = 300  # 5 دقیقه

async def check_proxy_advanced(proxy_config: config.ProxyConfig) -> bool:
    """بررسی پیشرفته وضعیت پروکسی"""
    current_time = time.time()
    cache_key = proxy_config.url
    
    if cache_key in _proxy_check_cache:
        cached_result, cache_time = _proxy_check_cache[cache_key]
        if current_time - cache_time < _proxy_check_cache_timeout:
            logger.debug(f"📋 استفاده از کش برای پروکسی: {proxy_config.url}")
            return cached_result
    
    try:
        timeout = aiohttp.ClientTimeout(total=config.PROXY_CONFIG['proxy_check_timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "https://httpbin.org/ip", 
                proxy=proxy_config.url,
                headers={'User-Agent': random.choice(config.CUSTOM_USER_AGENTS)}
            ) as resp:
                success = resp.status == 200
                if success:
                    config.proxy_manager.mark_success(proxy_config.url)
                    data = await resp.json()
                    logger.debug(f"✅ پروکسی {proxy_config.url} فعال است - IP: {data.get('origin', 'Unknown')}")
                else:
                    config.proxy_manager.mark_failed(proxy_config.url)
                    logger.warning(f"⚠️ پروکسی {proxy_config.url} پاسخ ناموفق: {resp.status}")
                _proxy_check_cache[cache_key] = (success, current_time)
                return success
    except asyncio.TimeoutError:
        logger.warning(f"⏰ تایم‌اوت در بررسی پروکسی {proxy_config.url}")
        config.proxy_manager.mark_failed(proxy_config.url)
        performance_monitor.record_proxy_failure()
        result = False
    except Exception as e:
        logger.debug(f"❌ پروکسی {proxy_config.url} فعال نیست: {str(e)[:100]}")
        config.proxy_manager.mark_failed(proxy_config.url)
        performance_monitor.record_proxy_failure()
        result = False
    
    _proxy_check_cache[cache_key] = (result, current_time)
    return result


async def get_active_proxies_advanced() -> List[Optional[config.ProxyConfig]]:
    """دریافت لیست پیشرفته پروکسی‌های فعال"""
    logger.info("🔍 در حال بررسی پیشرفته پروکسی‌ها...")
    
    if not config.proxy_manager:
        logger.warning("⚠️ مدیر پروکسی در دسترس نیست")
        return [None] if config.INCLUDE_NO_PROXY else []
    
    active_proxies = []
    
    if config.proxy_manager.active_proxies:
        logger.info(f"📊 در حال بررسی {len(config.proxy_manager.active_proxies)} پروکسی فعال...")
        
        semaphore = asyncio.Semaphore(10)
        
        async def check_with_semaphore(proxy_config):
            async with semaphore:
                return await check_proxy_advanced(proxy_config)
        
        check_tasks = [check_with_semaphore(proxy) for proxy in config.proxy_manager.active_proxies]
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        for i, (proxy_config, result) in enumerate(zip(config.proxy_manager.active_proxies, results)):
            if isinstance(result, Exception):
                logger.error(f"❌ خطا در بررسی پروکسی {proxy_config.url}: {result}")
                config.proxy_manager.mark_failed(proxy_config.url)
            elif result:
                active_proxies.append(proxy_config)
                logger.info(f"✅ پروکسی فعال: {proxy_config.url} ({proxy_config.country}, {proxy_config.latency}ms)")
            else:
                logger.warning(f"❌ پروکسی غیرفعال: {proxy_config.url}")
    
    if config.INCLUDE_NO_PROXY:
        active_proxies.append(None)
        logger.info("✅ حالت بدون پروکسی اضافه شد")
    
    if config.PROXY_CONFIG['save_proxy_stats']:
        config.proxy_manager.save_config()
    
    logger.info(f"📊 آمار نهایی پروکسی‌ها:")
    logger.info(f"   • کل پروکسی‌ها: {len(config.proxy_manager.proxies)}")
    logger.info(f"   • پروکسی‌های فعال: {len(active_proxies) - (1 if config.INCLUDE_NO_PROXY else 0)}")
    
    return active_proxies


async def select_best_proxy() -> Optional[config.ProxyConfig]:
    """انتخاب بهترین پروکسی"""
    if not config.proxy_manager:
        return None
    
    best_proxy = config.proxy_manager.get_best_proxy()
    
    if best_proxy:
        logger.info(f"🎯 بهترین پروکسی: {best_proxy.url} (موفقیت: {best_proxy.success_rate:.1%}, تأخیر: {best_proxy.latency}ms)")
    else:
        logger.warning("⚠️ هیچ پروکسی مناسبی یافت نشد")
    
    return best_proxy

# ==================== Human-like Behavior ====================

async def human_mouse_movement(page: Page) -> None:
    try:
        movements = random.randint(*config.MOUSE_MOVEMENTS_RANGE)
        for _ in range(movements):
            x = random.randint(50, 1000)
            y = random.randint(50, 700)
            steps = random.randint(10, 25)
            await page.mouse.move(x, y, steps=steps)
            await asyncio.sleep(random.uniform(0.2, 0.8))
    except Exception as e:
        logger.debug(f"خطا در حرکت موس: {e}")


async def natural_scroll(page: Page, passes: int = None) -> None:
    if passes is None:
        passes = random.randint(config.PAGE_SCROLL_PASSES - 2, config.PAGE_SCROLL_PASSES + 2)
    try:
        viewport_height = await page.evaluate("window.innerHeight")
        total_height = await page.evaluate("document.body.scrollHeight")
        logger.info(f"📜 اسکرول در {passes} مرحله...")
        current_position = 0
        for i in range(passes):
            scroll_ratio = random.uniform(*config.SCROLL_VIEWPORT_RATIO)
            scroll_amount = int(viewport_height * scroll_ratio)
            await page.evaluate(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")
            current_position += scroll_amount
            delay = human_delay(*config.SCROLL_DELAY_RANGE)
            logger.debug(f"   مرحله {i+1}/{passes} - تاخیر {delay:.1f}s")
            await asyncio.sleep(delay)
            if random.random() < 0.3:
                read_pause = random.uniform(2, 5)
                logger.debug(f"   ⏸️  توقف برای خواندن: {read_pause:.1f}s")
                await asyncio.sleep(read_pause)
            page_offset = await page.evaluate("window.pageYOffset + window.innerHeight")
            if page_offset >= total_height * 0.95:
                logger.debug("   ✅ به انتهای صفحه رسیدیم")
                break
        if random.random() < config.BACK_TO_TOP_CHANCE:
            logger.debug("   🔝 بازگشت به بالای صفحه")
            await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await asyncio.sleep(random.uniform(1, 2))
    except Exception as e:
        logger.warning(f"خطا در اسکرول: {e}")


async def random_interactions(page: Page) -> None:
    try:
        await human_mouse_movement(page)
        if random.random() < config.CLICK_CHANCE:
            clickables = await page.get_by_role("link").or_(page.get_by_role("button")).all()
            if len(clickables) > 5:
                element = random.choice(clickables[2:min(15, len(clickables))])
                await element.click(timeout=3000, no_wait_after=True)
                await asyncio.sleep(random.uniform(1, 3))
        scroll_amount = random.randint(50, 300)
        await page.evaluate(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")
        await asyncio.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        logger.debug(f"خطا در تعاملات: {e}")

# ==================== CAPTCHA Handling ====================

async def handle_captcha(page: Page, engine_name: str = "") -> bool:
    logger.critical("\n" + "="*70)
    logger.critical(f"⚠️  CAPTCHA شناسایی شد در {engine_name}")
    logger.critical("="*70)
    if config.SAVE_SCREENSHOTS:
        screenshot_path = SCREENSHOT_DIR / f"captcha_{engine_name}_{datetime.now():%H%M%S}.png"
        await page.screenshot(path=screenshot_path)
        logger.info(f"📸 اسکرین‌شات: {screenshot_path}")
    logger.info("✋ مرورگر باز است. لطفاً CAPTCHA را حل کنید...")
    try:
        user_input = input(f"❓ بعد از حل CAPTCHA، 'ok' بزنید (یا {config.CAPTCHA_MAX_WAIT}s صبر می‌کنم): ")
        if user_input.lower() in ['ok', 'yes', 'y', '']:
            await asyncio.sleep(2)
            return True
        else:
            logger.warning("⏭️  رد شدن از این موتور...")
            return False
    except KeyboardInterrupt:
        logger.warning("⚠️ کاربر لغو کرد")
        return False

# ==================== Internal Links ====================

async def extract_internal_links(page: Page, current_url: str, target_domain: str) -> List[str]:
    internal_links = []
    try:
        crawl_selectors = config.get_deep_crawl_selectors(target_domain)
        selector_string = ", ".join(crawl_selectors)
        anchors = await page.locator(selector_string).all()
        for anchor in anchors[:50]:
            href = await anchor.get_attribute('href')
            if href:
                full_url = urljoin(current_url, href)
                if is_same_domain(full_url, target_domain):
                    cleaned_url = urljoin(full_url, urlparse(full_url).path)
                    if cleaned_url not in internal_links and cleaned_url != current_url:
                        internal_links.append(cleaned_url)
        internal_links = list(dict.fromkeys(internal_links))
    except Exception as e:
        logger.debug(f"خطا در استخراج لینک‌های داخلی: {e}")
    return internal_links

# ==================== Natural Page Visit ====================

async def visit_page_naturally(
    page: Page,
    url: str,
    target_domain: str,
    is_from_search: bool = False
) -> bool:
    start_time = datetime.now()
    logger.info(f"🌐 بازدید طبیعی: {url[:80]}...")
    for attempt in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=config.PAGE_LOAD_TIMEOUT)
            await page.wait_for_load_state("networkidle", timeout=15000)
            logger.info(f"   ✅ صفحه بارگذاری شد")
            initial_delay = human_delay(2, 4)
            await asyncio.sleep(initial_delay)
            await random_interactions(page)
            scroll_passes = random.randint(3, 6)
            await natural_scroll(page, passes=scroll_passes)
            stay_time = random.uniform(15, 35)
            logger.info(f"   ⏱️  ماندن: {stay_time:.1f}s")
            num_phases = random.randint(2, 4)
            phase_time = stay_time / num_phases
            for phase in range(num_phases):
                await asyncio.sleep(phase_time * random.uniform(0.8, 1.2))
                if random.random() < 0.5:
                    await random_interactions(page)
            logger.info(f"   ✅ بازدید کامل شد")
            duration = (datetime.now() - start_time).total_seconds()
            performance_monitor.record_visit(success=True, duration=duration)
            return True
        except PlaywrightTimeout:
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"   ❌ خطا در بازدید (تلاش {attempt+1}): {e}")
    
    performance_monitor.record_visit(success=False)
    performance_monitor.record_error(f"خطا در بازدید {url}")
    return False

# ==================== Smart Click and Visit ====================

async def smart_click_and_visit(
    page: Page,
    search_results: List[Tuple[int, str]],
    target_domain: str,
    search_engine_url: str
) -> None:
    num_cycles = random.randint(3, 7)
    logger.info(f"\n🔄 شروع چرخه بازدید هوشمند ({num_cycles} بار)")
    visited_urls = set()
    for cycle in range(1, num_cycles + 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"🔁 چرخه {cycle}/{num_cycles}")
        logger.info(f"{'='*60}")
        current_url = page.url
        if cycle == 1 or random.random() < 0.4 or current_url == search_engine_url:
            if current_url != search_engine_url:
                logger.info("   🔙 بازگشت به صفحه جستجو...")
                await page.goto(search_engine_url, wait_until="domcontentloaded")
                await asyncio.sleep(human_delay(2, 4))
            available_links = [
                (rank, url) for rank, url in search_results 
                if url not in visited_urls and is_same_domain(url, target_domain)
            ]
            if not available_links:
                available_links = [
                    (rank, url) for rank, url in search_results 
                    if is_same_domain(url, target_domain)
                ]
            if not available_links:
                logger.warning("   ❌ هیچ لینکی برای بازدید وجود ندارد")
                break
            selected_rank, selected_url = random.choice(available_links[:3]) if len(available_links) > 3 else random.choice(available_links)
            logger.info(f"   🎯 لینک انتخابی: رتبه {selected_rank}")
            logger.info(f"   🔗 {selected_url[:70]}...")
            visited_urls.add(selected_url)
            await asyncio.sleep(random.uniform(1, 3))
            success = await visit_page_naturally(page, selected_url, target_domain, is_from_search=True)
            if not success:
                continue
        else:
            logger.info("🔗 استخراج و باز کردن لینک داخلی...")
            internal_links = await extract_internal_links(page, current_url, target_domain)
            if internal_links:
                available_internal = [link for link in internal_links if link not in visited_urls]
                if not available_internal:
                    available_internal = internal_links
                selected_internal = random.choice(available_internal[:3]) if len(available_internal) > 3 else random.choice(available_internal)
                logger.info(f"   🔗 لینک داخلی: {selected_internal[:70]}...")
                visited_urls.add(selected_internal)
                success = await visit_page_naturally(page, selected_internal, target_domain, is_from_search=False)
                if not success:
                    continue
            else:
                logger.info("   ℹ️  لینک داخلی یافت نشد - بازگشت به جستجو در چرخه بعد")
        if cycle < num_cycles:
            delay = human_delay(5, 12)
            logger.info(f"\n⏳ تاخیر {delay:.1f}s تا چرخه بعدی...")
            await asyncio.sleep(delay)
    logger.info(f"\n✅ چرخه بازدید هوشمند کامل شد ({len(visited_urls)} صفحه بازدید شد)")

# ==================== Request Interception ====================

async def intercept_route(route: Route) -> None:
    resource_type = route.request.resource_type
    if resource_type in ['image', 'media', 'font']:
        await route.abort()
    else:
        await route.continue_()

# ==================== Search in Engine ====================

async def search_in_engine(
    page: Page,
    engine_config: Dict,
    max_results: int = config.MAX_RESULTS_TO_CHECK
) -> List[Tuple[int, str]]:
    start_time = datetime.now()
    engine_name = engine_config["name"]
    url = engine_config["url"]
    selectors = engine_config["selectors"]
    exclude_domains = engine_config.get("exclude_domains", [])
    logger.info(f"\n🔍 جستجو در {engine_name}...")
    results = []
    rank = 1
    seen_urls = set()
    try:
        await page.route("**/*", intercept_route)
        await page.goto(url, wait_until="domcontentloaded", timeout=config.PAGE_LOAD_TIMEOUT)
        await asyncio.sleep(human_delay(*config.HUMAN_DELAY_RANGE))
        content_lower = (await page.content()).lower()
        if any(kw in content_lower for kw in ['captcha', 'robot', 'unusual traffic', 'verify']):
            performance_monitor.record_captcha()
            if not await handle_captcha(page, engine_name):
                return []
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
        await random_interactions(page)
        working_locator = None
        priority_selectors = engine_config.get("priority_selectors", [])
        if priority_selectors:
            for selector in priority_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=8000)
                    count = await page.locator(selector).count()
                    if count > 0:
                        working_locator = page.locator(selector)
                        logger.info(f"   ✅ انتخابگر با اولویت کار کرد: {count} نتیجه")
                        break
                except PlaywrightTimeout:
                    continue
        if not working_locator:
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=6000)
                    count = await page.locator(selector).count()
                    if count > 0:
                        working_locator = page.locator(selector)
                        logger.info(f"   ✅ انتخابگر کار کرد: {count} نتیجه")
                        break
                except PlaywrightTimeout:
                    continue
        if not working_locator:
            logger.error(f"   ❌ هیچ انتخابگری کار نکرد!")
            if any(config.FALLBACK_STRATEGIES.values()):
                logger.info(f"   🔄 تلاش برای استخراج URL با استراتژی‌های fallback...")
                all_fallback_urls = []
                if config.FALLBACK_STRATEGIES.get("extract_from_text", True):
                    all_fallback_urls.extend(await extract_urls_from_text(page, exclude_domains))
                if config.FALLBACK_STRATEGIES.get("extract_from_meta", True):
                    all_fallback_urls.extend(await extract_urls_from_meta(page, exclude_domains))
                if config.FALLBACK_STRATEGIES.get("extract_from_scripts", True):
                    all_fallback_urls.extend(await extract_urls_from_scripts(page, exclude_domains))
                if config.FALLBACK_STRATEGIES.get("extract_from_images", True):
                    all_fallback_urls.extend(await extract_urls_from_images(page, exclude_domains))
                unique_urls = list(dict.fromkeys(all_fallback_urls))
                if unique_urls:
                    logger.info(f"   ✅ {len(unique_urls)} URL با استراتژی‌های fallback استخراج شد")
                    for u in unique_urls[:max_results]:
                        if u not in seen_urls:
                            seen_urls.add(u)
                            results.append((rank, u))
                            rank += 1
                    return results
            if config.SAVE_SCREENSHOTS:
                screenshot_path = SCREENSHOT_DIR / f"error_{engine_name}_{datetime.now():%H%M%S}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"   📸 اسکرین‌شات خطا: {screenshot_path}")
            return []
        for scroll_round in range(config.MAX_SCROLL_ROUNDS):
            anchors = await working_locator.all()
            new_links = 0
            for anchor in anchors:
                href = await anchor.get_attribute('href')
                if href and is_valid_url(href, exclude_domains):
                    if href not in seen_urls:
                        seen_urls.add(href)
                        results.append((rank, href))
                        rank += 1
                        new_links += 1
                        if len(results) >= max_results:
                            break
            logger.debug(f"      دور {scroll_round + 1}: {new_links} لینک جدید")
            if len(results) >= max_results:
                break
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(2, 4))
        logger.info(f"   ✅ {len(results)} نتیجه یافت شد")
        if results:
            logger.debug(f"   📋 نمونه نتایج:")
            for r, link in results[:3]:
                logger.debug(f"      {r}. {link[:60]}...")
        
        duration = (datetime.now() - start_time).total_seconds()
        performance_monitor.record_search(success=True, duration=duration)
        
        return results
    except Exception as e:
        logger.error(f"   ❌ خطا در {engine_name}: {e}")
        performance_monitor.record_search(success=False)
        performance_monitor.record_error(f"خطا در {engine_name}: {str(e)}")
        return []

# ==================== Browser Management ====================

_browser_pool = {}
_browser_pool_max_size = 3

async def get_browser_from_pool(playwright: Playwright, proxy_config: Optional[config.ProxyConfig] = None) -> Browser:
    """دریافت مرورگر از استخر یا ایجاد جدید"""
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
    """پاکسازی استخر مرورگرها"""
    global _browser_pool
    for proxy_key, browser_info in list(_browser_pool.items()):
        try:
            await browser_info['browser'].close()
        except Exception:
            pass
    _browser_pool.clear()

async def launch_browser_with_proxy(playwright: Playwright, proxy_config: Optional[config.ProxyConfig] = None) -> Browser:
    """راه‌اندازی مرورگر با پروکسی مشخص"""
    
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
        headless=config.HEADLESS,
        args=browser_args,
        proxy=proxy_dict,
        ignore_default_args=["--enable-automation"],
    )
    
    return browser

# ==================== Device Processing ====================

async def process_device(
    playwright: Playwright,
    browser: Browser,
    device_name: str,
    proxy: Optional[config.ProxyConfig],
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
    
    await context.tracing.start(name=f"trace_{device_name}", screenshots=True, snapshots=True)
    page = await context.new_page()
    try:
        if do_search:
            logger.info("\n🔍 حالت: جستجو و بازدید هوشمند")
            for query in queries:
                logger.info(f"\n   🔎 کوئری: {query}")
                active_engines = [e for e in config.get_search_engines(query) if e.get("enabled", True)]
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
                    target_results = [(rank, url) for rank, url in results if is_same_domain(url, target_domain)]
                    if target_results:
                        await smart_click_and_visit(page, results, target_domain, engine["url"])
                    delay = human_delay(*config.BETWEEN_ENGINES_DELAY)
                    logger.info(f"\n⏳ تاخیر {delay:.1f}s تا موتور بعدی...")
                    await asyncio.sleep(delay)
        if do_direct_visit:
            logger.info("\n🎯 حالت: بازدید مستقیم")
            num_to_visit = min(3, len(direct_urls))
            selected_urls = random.sample(direct_urls, num_to_visit)
            for direct_url in selected_urls:
                await asyncio.sleep(human_delay(*config.BETWEEN_PAGES_DELAY))
                success = await visit_page_naturally(page, direct_url, target_domain, is_from_search=False)
                if success and random.random() < 0.7:
                    internal_links = await extract_internal_links(page, direct_url, target_domain)
                    if internal_links:
                        num_internal = min(2, len(internal_links))
                        selected_internal = random.sample(internal_links, num_internal)
                        logger.info(f"\n🔗 بازدید {num_internal} لینک داخلی...")
                        for internal_url in selected_internal:
                            await asyncio.sleep(human_delay(5, 10))
                            await visit_page_naturally(page, internal_url, target_domain, is_from_search=False)
        logger.info(f"\n✅ پردازش {device_name} برای {target_domain} کامل شد")
    except Exception as e:
        logger.error(f"❌ خطای کلی در {device_name} برای {target_domain}: {e}", exc_info=True)
    finally:
        await context.tracing.stop(path=f"trace_{target_domain}_{device_name}.zip")
        await context.close()
        await asyncio.sleep(random.uniform(2, 4))


# ==================== Main Function ====================

async def main():
    logger.info("="*80)
    logger.info("🚀 ربات SEO - شروع برنامه (نسخه بازدید هوشمند)")
    logger.info("="*80)
    logger.info(f"🎯 تعداد اهداف: {len(config.TARGETS)}")
    logger.info(f"📱 تعداد دستگاه‌ها: {len(config.DEVICES)}")
    logger.info(f"⚙️  حالت‌های فعال: {[k for k, v in config.MODES.items() if v]}")
    logger.info("="*80)
    
    active_proxies = config.get_active_proxies_advanced()  # بدون await، چون sync است
    if not active_proxies:
        logger.error("❌ هیچ پروکسی فعالی یافت نشد!")
        return
    
    logger.info(f"🔌 تعداد پروکسی‌های فعال بارگذاری‌شده از CSV: {len(active_proxies)}")
    
    async with async_playwright() as playwright:
        semaphore = asyncio.Semaphore(3)
        
        async def process_target(target):
            async with semaphore:
                proxy_rotation_list = active_proxies if config.USE_PROXY_ROTATION else [random.choice(active_proxies)]
                
                for proxy in proxy_rotation_list:
                    proxy_str = proxy.url if proxy else 'بدون پروکسی'
                    logger.info(f"\n🔌 پروکسی: {proxy_str} (برای {target['TARGET_DOMAIN']})")
                    
                    try:
                        browser = await get_browser_from_pool(playwright, proxy)
                        
                        num_devices = random.randint(1, min(3, len(config.DEVICES)))
                        selected_devices = random.sample(config.DEVICES, num_devices)
                        
                        for device in selected_devices:
                            await process_device(playwright, browser, device, proxy, target)
                            delay = random.uniform(10, 20)
                            await asyncio.sleep(delay)
                        
                        if proxy_rotation_list.index(proxy) < len(proxy_rotation_list) - 1:
                            delay = random.uniform(15, 30)
                            await asyncio.sleep(delay)
                            
                    except Exception as e:
                        logger.error(f"❌ خطا در استفاده از پروکسی {proxy_str}: {e}")
                        if proxy:
                            config.proxy_manager.mark_failed(proxy.url)
                        continue
        
        tasks = [process_target(target) for target in config.TARGETS]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        await cleanup_browser_pool()
    
    logger.info("\n" + "="*80)
    logger.info("✅ برنامه با موفقیت به پایان رسید")
    logger.info("="*80)
    
    summary = performance_monitor.get_summary()
    logger.info("\n📊 آمار نهایی عملکرد:")
    logger.info(f"   ⏱️  زمان اجرا: {summary['runtime_minutes']:.1f} دقیقه")
    logger.info(f"   🔍 نرخ موفقیت جستجو: {summary['search_success_rate']:.1f}%")
    logger.info(f"   🌐 نرخ موفقیت بازدید: {summary['visit_success_rate']:.1f}%")
    logger.info(f"   📊 میانگین زمان جستجو: {summary['avg_search_time']:.1f} ثانیه")
    logger.info(f"   ⏰ میانگین زمان بازدید: {summary['avg_visit_time']:.1f} ثانیه")
    logger.info(f"   ❌ تعداد خطاها: {summary['total_errors']}")
    logger.info(f"   🔌 نرخ شکست پروکسی: {summary['proxy_failure_rate']:.1f}%")
    logger.info(f"   🤖 نرخ مواجهه با CAPTCHA: {summary['captcha_rate']:.1f}%")
    
    performance_monitor.save_report()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("\n⚠️ برنامه توسط کاربر متوقف شد")
    except Exception as e:
        logger.critical(f"❌ خطای بحرانی: {e}", exc_info=True)
        sys.exit(1)