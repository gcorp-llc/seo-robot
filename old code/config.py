from urllib.parse import quote_plus
import csv
import os
import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

# تنظیمات لاگینگ ساده برای config (خطاها در logs/config_errors.log ذخیره شود)
logging.basicConfig(
    filename='logs/config_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# تلاش برای بارگذاری python-dotenv؛ اگر نصب نبود، fallback ساده ارائه می‌شود
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        logging.warning("پکیج 'python-dotenv' نصب نیست؛ متغیرهای محیطی از فایل .env بارگذاری نخواهند شد.")
        return

# بارگذاری متغیرهای محیطی
load_dotenv()

# ==================== سیستم مدیریت پروکسی پیشرفته ====================

class ProxyType(Enum):
    """انواع پروکسی"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

@dataclass
class ProxyConfig:
    """کلاس پیکربندی پروکسی با ویژگی‌های پیشرفته"""
    url: str
    ip: str
    port: int
    protocol: ProxyType
    country: str = "Unknown"
    latency: int = 0
    is_active: bool = True
    failure_count: int = 0
    last_used: Optional[str] = None
    success_rate: float = 1.0
    
    def __post_init__(self):
        """تنظیمات پس از ایجاد شی"""
        if isinstance(self.protocol, str):
            self.protocol = ProxyType(self.protocol.lower())
        if isinstance(self.port, str):
            self.port = int(self.port)
        if isinstance(self.latency, str):
            self.latency = int(self.latency.replace(' ms', ''))
    
    def to_dict(self) -> Dict[str, Any]:
        """تبدیل به دیکشنری برای ذخیره‌سازی"""
        return {
            'url': self.url,
            'ip': self.ip,
            'port': self.port,
            'protocol': self.protocol.value,
            'country': self.country,
            'latency': self.latency,
            'is_active': self.is_active,
            'failure_count': self.failure_count,
            'last_used': self.last_used,
            'success_rate': self.success_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxyConfig':
        """ایجاد از دیکشنری"""
        return cls(**data)

class ProxyManager:
    """مدیریت پیشرفته پروکسی‌ها - فقط از فایل CSV استفاده می‌کند"""
    
    def __init__(self):
        self.proxies: List[ProxyConfig] = []
        self.active_proxies: List[ProxyConfig] = []
        # فقط از CSV بارگذاری می‌کند - هیچ فایل JSONی در کار نیست
        self.load_proxies_from_csv()
    
    def add_proxy(self, proxy: ProxyConfig):
        """افزودن پروکسی جدید"""
        self.proxies.append(proxy)
        if proxy.is_active:
            self.active_proxies.append(proxy)
    
    def remove_proxy(self, url: str):
        """حذف پروکسی"""
        self.proxies = [p for p in self.proxies if p.url != url]
        self.active_proxies = [p for p in self.active_proxies if p.url != url]
    
    def mark_failed(self, url: str):
        """علامت‌گذاری پروکسی به عنوان ناموفق"""
        for proxy in self.proxies:
            if proxy.url == url:
                proxy.failure_count += 1
                proxy.success_rate = max(0.0, proxy.success_rate - 0.1)
                if proxy.failure_count >= 3:  # حداکثر 3 شکست
                    proxy.is_active = False
                    self.active_proxies = [p for p in self.active_proxies if p.url != url]
                break
    
    def mark_success(self, url: str):
        """علامت‌گذاری پروکسی به عنوان موفق"""
        for proxy in self.proxies:
            if proxy.url == url:
                proxy.success_rate = min(1.0, proxy.success_rate + 0.05)
                proxy.last_used = self._get_current_time()
                break
    
    def get_best_proxy(self) -> Optional[ProxyConfig]:
        """دریافت بهترین پروکسی بر اساس معیارها"""
        if not self.active_proxies:
            return None
        
        # مرتب‌سازی بر اساس موفقیت، تأخیر و آخرین استفاده
        sorted_proxies = sorted(
            self.active_proxies,
            key=lambda p: (p.success_rate, -p.latency, p.last_used or ''),
            reverse=True
        )
        
        # انتخاب تصادفی از 5 پروکسی برتر
        top_proxies = sorted_proxies[:5]
        return random.choice(top_proxies) if top_proxies else None
    
    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """دریافت پروکسی تصادفی"""
        return random.choice(self.active_proxies) if self.active_proxies else None
    
    def get_proxy_by_country(self, country: str) -> Optional[ProxyConfig]:
        """دریافت پروکسی بر اساس کشور"""
        country_proxies = [p for p in self.active_proxies if p.country.lower() == country.lower()]
        return random.choice(country_proxies) if country_proxies else None
    
    def get_proxy_by_latency(self, max_latency: int) -> Optional[ProxyConfig]:
        """دریافت پروکسی با تأخیر مشخص"""
        fast_proxies = [p for p in self.active_proxies if p.latency <= max_latency]
        return random.choice(fast_proxies) if fast_proxies else None
    
    def get_all_proxy_urls(self) -> List[str]:
        """دریافت لیست تمام URLهای پروکسی"""
        return [p.url for p in self.proxies]
    
    def get_active_proxy_urls(self) -> List[str]:
        """دریافت لیست URLهای پروکسی فعال"""
        return [p.url for p in self.active_proxies]
    
    def load_proxies_from_csv(self):
        """بارگذاری پروکسی‌ها فقط از طریق CSV - بدون وابستگی به JSON"""
        try:
            # استفاده از لیست سراسری که قبلاً بارگذاری شده است
            global _loaded_proxies_from_csv
            
            if '_loaded_proxies_from_csv' in globals() and _loaded_proxies_from_csv:
                proxies = _loaded_proxies_from_csv
            else:
                # اگر قبلاً بارگذاری نشده بود، بارگذاری جدید انجام بده
                proxies = load_proxies_from_csv_advanced()
            
            # اضافه کردن به لیست داخلی
            for proxy in proxies:
                self.add_proxy(proxy)
                
            print(f"✅ {len(proxies)} پروکسی از CSV بارگذاری شد")
            
        except Exception as e:
            logging.error(f"خطا در بارگذاری پیکربندی پروکسی از CSV: {e}")
            self.proxies = []
            self.active_proxies = []
    
    def _get_current_time(self) -> str:
        """دریافت زمان فعلی"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def __len__(self):
        return len(self.proxies)
    
    def __bool__(self):
        return bool(self.active_proxies)

# ==================== توابع کمکی برای پروکسی ====================

def validate_proxy_format(proxy_url: str) -> bool:
    """اعتبارسنجی فرمت پروکسی"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(proxy_url)
        
        # بررسی پروتکل
        if parsed.scheme not in ['http', 'https', 'socks4', 'socks5']:
            return False
        
        # بررسی آی‌پی و پورت
        if not parsed.hostname or not parsed.port:
            return False
        
        # بررسی محدوده پورت
        if not (1 <= parsed.port <= 65535):
            return False
        
        return True
    except Exception:
        return False

def filter_proxies_by_criteria(proxies: List[ProxyConfig], 
                             max_latency: int = 500,
                             min_success_rate: float = 0.7,
                             countries: List[str] = None) -> List[ProxyConfig]:
    """فیلتر پروکسی‌ها بر اساس معیارها"""
    filtered = []
    
    for proxy in proxies:
        if (proxy.latency <= max_latency and 
            proxy.success_rate >= min_success_rate and
            proxy.is_active):
            
            if countries and proxy.country not in countries:
                continue
                
            filtered.append(proxy)
    
    return filtered

def create_proxy_from_csv_row(row: Dict[str, str]) -> Optional[ProxyConfig]:
    """ایجاد پروکسی از ردیف CSV با فرمت جدید"""
    try:
        ip = row.get('IP', '').strip().strip('"')
        port = row.get('Port', '').strip().strip('"')
        protocol_str = row.get('Protocol', 'HTTP').strip().strip('"')
        country = row.get('Country', 'Unknown').strip().strip('"')
        latency_str = row.get('Latency', '0').strip().strip('"')
        # Type و Google و Last checked رو ignore می‌کنیم چون در ProxyConfig لازم نیستن
        
        if not ip or not port:
            return None
        
        # تبدیل پروتکل
        protocol_map = {
            'HTTP': 'http',
            'HTTPS': 'https', 
            'SOCKS4': 'socks4',
            'SOCKS5': 'socks5'
        }
        
        protocol = protocol_map.get(protocol_str.upper(), 'http')
        port_int = int(port)
        latency_int = int(latency_str.replace(' ms', '')) if ' ms' in latency_str else int(latency_str)
        
        proxy_url = f"{protocol}://{ip}:{port_int}"
        
        return ProxyConfig(
            url=proxy_url,
            ip=ip,
            port=port_int,
            protocol=protocol,
            country=country,
            latency=latency_int,
            is_active=True
        )
    except Exception as e:
        logging.error(f"خطا در ایجاد پروکسی از CSV: {e} - ردیف: {row}")
        return None

# ==================== تابع بهبود یافته بارگذاری CSV ====================

def load_proxies_from_csv_advanced(csv_file: str = "proxies-export.csv", 
                                 max_proxies: int = 0,  # 0 یعنی همه
                                 min_latency: int = 0,
                                 max_latency: int = 500,
                                 preferred_countries: List[str] = None) -> List[ProxyConfig]:
    """
    بارگذاری پیشرفته پروکسی‌ها از فایل CSV با فیلترینگ هوشمند
    """
    
    proxies = []
    csv_path = Path(csv_file)
    
    if not csv_path.exists():
        logging.error(f"فایل {csv_file} یافت نشد.")
        print(f"⚠️ فایل {csv_file} یافت نشد. لیست پروکسی خالی خواهد بود.")
        return proxies
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                proxy = create_proxy_from_csv_row(row)
                
                if proxy and validate_proxy_format(proxy.url):
                    # فیلتر بر اساس تأخیر
                    if min_latency <= proxy.latency <= max_latency:
                        # فیلتر بر اساس کشورهای ترجیحی
                        if preferred_countries:
                            if proxy.country in preferred_countries:
                                proxies.append(proxy)
                        else:
                            proxies.append(proxy)
                
                # اگر max_proxies > 0، توقف اگر به حداکثر رسیدیم
                if max_proxies > 0 and len(proxies) >= max_proxies:
                    break
            
            # مرتب‌سازی بر اساس تأخیر و موفقیت
            proxies.sort(key=lambda p: (p.latency, -p.success_rate))
            
            print(f"✅ {len(proxies)} پروکسی از فایل {csv_file} بارگذاری شد")
            
            # نمایش آمار
            if proxies:
                countries = {}
                for proxy in proxies:
                    countries[proxy.country] = countries.get(proxy.country, 0) + 1
                
                print(f"📊 آمار پروکسی‌ها:")
                print(f"   • تعداد کل: {len(proxies)}")
                print(f"   • میانگین تأخیر: {sum(p.latency for p in proxies) // len(proxies)} ms")
                print(f"   • کشورها: {dict(list(countries.items())[:5])}")
                
                # نمایش نمونه‌ها
                print(f"📋 نمونه پروکسی‌های بارگذاری شده:")
                for i, proxy in enumerate(proxies[:3], 1):
                    print(f"   {i}. {proxy.url} ({proxy.country}, {proxy.latency}ms)")
                if len(proxies) > 3:
                    print(f"   ... و {len(proxies) - 3} پروکسی دیگر")
            
            # ذخیره در لیست سراسری برای استفاده در ProxyManager
            global _loaded_proxies_from_csv
            _loaded_proxies_from_csv = proxies
            
            return proxies
        
    except Exception as e:
        logging.error(f"خطا در خواندن فایل CSV: {e}")
        print(f"❌ خطا در خواندن فایل CSV: {e}")
        print(f"⚠️ لیست پروکسی خالی خواهد بود")
        return []

# ==================== تنظیمات مدیریت پروکسی (برای سازگاری با کد قبلی)
# تنظیمات پیشرفته پروکسی - حذف proxy_config_file
PROXY_CONFIG = {
    'max_proxies': int(os.getenv('MAX_PROXIES', '0')),  # 0 یعنی همه
    'min_latency': int(os.getenv('MIN_LATENCY', '0')),                
    'max_latency': int(os.getenv('MAX_LATENCY', '1000')),             
    'preferred_countries': [        
        'United States', 'Germany', 'Netherlands', 'United Kingdom', 'Canada'
    ],
    'proxy_check_timeout': int(os.getenv('PROXY_CHECK_TIMEOUT', '15')),     
    'use_proxy_rotation': os.getenv('USE_PROXY_ROTATION', 'true').lower() == 'true',      
    'include_no_proxy': os.getenv('INCLUDE_NO_PROXY', 'false').lower() == 'true',       
    'max_retries_per_proxy': int(os.getenv('MAX_RETRIES_PER_PROXY', '2')),      
    'proxy_failure_threshold': int(os.getenv('PROXY_FAILURE_THRESHOLD', '3')),    
    'save_proxy_stats': os.getenv('SAVE_PROXY_STATS', 'true').lower() == 'true'       
    # proxy_config_file حذف شد - فقط از CSV استفاده می‌کنیم
}

# پس از تعریف PROXY_CONFIG مقداردهی ثابت‌های ماژول انجام می‌شود
PROXY_CHECK_TIMEOUT = PROXY_CONFIG['proxy_check_timeout']
USE_PROXY_ROTATION = PROXY_CONFIG['use_proxy_rotation']
INCLUDE_NO_PROXY = PROXY_CONFIG['include_no_proxy']
MAX_RETRIES_PER_PROXY = PROXY_CONFIG['max_retries_per_proxy']

# تنظیمات امنیتی پروکسی
PROXY_SECURITY = {
    'validate_ssl': True,            
    'block_private_ips': True,       
    'block_reserved_ips': True,      
    'max_concurrent_requests': 10,   
    'request_delay_range': (1, 3),   
}

# بارگذاری پروکسی‌ها فقط از فایل CSV - حذف proxy_config_file
print("🔄 در حال بارگذاری پروکسی‌ها فقط از فایل CSV...")

# ایجاد مدیر پروکسی - فقط از CSV استفاده می‌کند
try:
    proxy_manager = ProxyManager()  # حذف پارامتر proxy_config_file
    
    print(f"✅ مدیر پروکسی با {len(proxy_manager)} پروکسی از CSV راه‌اندازی شد")
    
except Exception as e:
    logging.error(f"خطا در راه‌اندازی مدیر پروکسی: {e}")
    proxy_manager = ProxyManager()  # مدیر خالی به عنوان پشتیبان

# لیست‌های پروکسی برای سازگاری با کد قبلی
PROXIES = proxy_manager.get_all_proxy_urls()
ACTIVE_PROXIES = proxy_manager.get_active_proxy_urls()

print(f"📊 آمار پروکسی‌ها:")
print(f"   • پروکسی‌های کل: {len(PROXIES)}")
print(f"   • پروکسی‌های فعال: {len(ACTIVE_PROXIES)}")

if ACTIVE_PROXIES:
    print(f"   • نمونه پروکسی فعال: {ACTIVE_PROXIES[0]}")
else:
    print("   ⚠️ هیچ پروکسی فعالی یافت نشد")

# ==================== تنظیمات Playwright و سایر تنظیمات عمومی ====================
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
DEFAULT_TIMEOUT = int(os.getenv('DEFAULT_TIMEOUT', '60000'))  # میلی‌ثانیه
PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', '45000'))  # میلی‌ثانیه
MAX_RESULTS_TO_CHECK = int(os.getenv('MAX_RESULTS_TO_CHECK', '30'))

# ==================== تنظیمات زمان‌بندی (ثانیه) ====================
HUMAN_DELAY_RANGE = (2.0, 4.5)
INTERACTION_DELAY_RANGE = (0.8, 2.0)
SCROLL_DELAY_RANGE = (3.0, 6.0)
BETWEEN_ENGINES_DELAY = (8, 15)
BETWEEN_PAGES_DELAY = (5, 10)
STAY_ON_PAGE_RANGE = (20, 40)

# ==================== تنظیمات اسکرول ====================
MAX_SCROLL_ROUNDS = 5
PAGE_SCROLL_PASSES = 8
SCROLL_VIEWPORT_RATIO = (0.5, 0.9)

# ==================== لیست دستگاه‌های موبایل ====================
DEVICES = [
    "iPhone 15 Pro Max",
    "iPhone 15 Pro",
    "iPhone 14 Pro Max",
    "iPhone 14 Pro",
    "iPhone 13 Pro",
    "iPhone 13",
    "iPhone 12 Pro",
    "iPhone 12",
    "Galaxy S24 Ultra",
    "Galaxy S23 Ultra",
    "Galaxy S23",
    "Galaxy S22",
    "Pixel 8 Pro",
    "Pixel 8",
    "Pixel 7 Pro",
    "Pixel 7",
    "Galaxy A54",
]

# ==================== فعال/غیرفعال سازی موتورهای جستجو ====================
SEARCH_ENGINES_ENABLED = {
    "Google": True,
    "Bing": True,
    "DuckDuckGo": True,
    "Yandex": True,
    "Yahoo": True,
    "Brave": True,
    "Ecosia": True,
    "Startpage": True,
}

# ==================== موتورهای جستجو ====================
def get_search_engines(query: str) -> list:
    """
    لیست موتورهای جستجو را بر اساس کوئری ورودی برمی‌گرداند.
    فقط موتورهای فعال شده در SEARCH_ENGINES_ENABLED برگردانده می‌شوند.
    """
    if not query:
        return []
        
    encoded_query = quote_plus(query)
    
    all_engines = [
        {
            "name": "Google",
            "enabled": SEARCH_ENGINES_ENABLED.get("Google", True),
            "url": f"https://www.google.com/search?q={encoded_query}&hl=fa&gl=IR",
            "selectors": [
                'a:has(h3.LC20lb):not([href*="google"])',
                'div.tF2Cxc a[href^="http"]:not([href*="google"])',
                'div.xfX4Ac a[href^="http"]:not([href*="google"])',
                'div.yuRUbf > a[href^="http"]:not([href*="google"])',
                'div[data-ved] > div[data-ved] > div[data-ved] a[jsname][href^="http"]:not([href*="google"])',
                'div#search div.g a[href^="http"]:not([href*="google"]):not([href*="youtube"])',
                'div[data-snf] a[href^="http"]:not([href*="google"])',
                'div[data-ved] > div a[href^="http"][data-ved]:not([href*="google"])',
                'div[data-hveid] a[href^="http"]:not([href*="google"])',
                'div[jscontroller] h3 a[href^="http"]:not([href*="google"])',
                'div[data-attrid] a[href^="http"]:not([href*="google"])',
                'div[data-md] a[href^="http"]:not([href*="google"])',
                'div[data-ved] div[role="heading"] a[href^="http"]:not([href*="google"])',
                'div.Gx5Zad a[href^="http"]:not([href*="google"])',
                'div.kp-blk a[href^="http"]:not([href*="google"])',
                'cite[role="text"]',
                'a[href^="http"]:not([href*="google.com"]):not([href*="youtube.com"]):not([href*="maps.google.com"])',
            ],
            "exclude_domains": ["google.com", "youtube.com", "maps.google.com", "accounts.google.com", "support.google.com", "googleadservices.com", "doubleclick.net"],
            "wait_for_selector": 'div#search, div#rso, div[data-ved], div.tF2Cxc, div.xfX4Ac, div.yuRUbf',
            "priority_selectors": [
                'a:has(h3.LC20lb):not([href*="google"])',
                'div.tF2Cxc a[href^="http"]:not([href*="google"])',
                'div.xfX4Ac a[href^="http"]:not([href*="google"])',
                'div.yuRUbf > a[href^="http"]:not([href*="google"])',
                'div[data-ved] > div[data-ved] > div[data-ved] a[jsname][href^="http"]:not([href*="google"])',
                'div[data-result-url] a',
                'a[jsname][data-ved]',
                'div.g a[href*="/url?q="]',
                'div[data-hveid] a[href^="http"]',
                'div[data-ved] a[href^="http"]',
                'a[ping][href^="http"]',
                'div[data-async-context] a',
                'g-link a[href^="http"]',
                'div[data-attrid] a',
                'a[data-ved][href*="/url?q="]'
            ],
        },
        {
            "name": "Bing",
            "enabled": SEARCH_ENGINES_ENABLED.get("Bing", True),
            "url": f"https://www.bing.com/search?q={encoded_query}&cc=IR&setlang=fa",
            "selectors": [
                'ol#b_results li.b_algo h2 a[href^="http"]:not([href*="bing.com"])',
                'li.b_algo div div.b_title h2 a[href^="http"]:not([href*="bing.com"])',
                'div.b_algo div.b_title div h2 a[href^="http"]:not([href*="bing.com"])',
                'main#b_content article[data-tag="DeepLink"] h2 a[href^="http"]:not([href*="bing.com"])',
                'article.b_algo h2 a[href^="http"]:not([href*="bing.com"])',
                'div.ttc a[href^="http"]:not([href*="bing.com"])',
                'div[data-tag="ChatAnswer"] a[href^="http"]:not([href*="bing.com"])',
                'div.ai_answer a[href^="http"]:not([href*="bing.com"])',
                'a.tilk[href^="http"]:not([href*="bing.com"])',
                'div[data-bm] a[href^="http"]:not([href*="bing.com"])',
                'cite',
                'div.b_attribution cite',
                'main a[href^="http"]:not([href*="bing.com"]):not([href*="microsoft.com"])',
                'div#content a[href^="http"]:not([href*="bing.com"]):not([href*="microsoft.com"])',
            ],
            "exclude_domains": ["bing.com", "microsoft.com", "msn.com", "live.com", "outlook.com"],
            "wait_for_selector": 'ol#b_results, main#b_content, article.b_algo',
            "priority_selectors": [
                'ol#b_results li.b_algo h2 a[href^="http"]:not([href*="bing.com"])',
                'article.b_algo h2 a[href^="http"]:not([href*="bing.com"])',
                'h2 a[href^="http"]',
                'li.b_algo h2 a',
                'div.b_title a',
                'a.tilk[href^="http"]',
                'div.b_algo h2 a',
                'h2 a[href^="https"]',
                'div.tpcn a',
                'a.sh_favicon',
                'div.b_caption a',
                'h2.b_topTitle a',
                'a.b_logoArea',
                'div.b_algoGroup a',
                'h2 a[target="_blank"]',
                'div.b_deep ul li a',
                'a.b_attribution'
            ],
        },
        {
            "name": "DuckDuckGo",
            "enabled": SEARCH_ENGINES_ENABLED.get("DuckDuckGo", True),
            "url": f"https://duckduckgo.com/?q={encoded_query}&kl=ir-fa",
            "selectors": [
                'article[data-result="organic"] h2 a[href^="http"]:not([href*="duckduckgo.com"])',
                'div[data-result="organic"] h2 a[href^="http"]:not([href*="duckduckgo.com"])',
                'ol[data-testid="mainline"] article h2 a[href^="http"]:not([href*="duckduckgo.com"])',
                'article[data-testid="result"] h2 a[data-testid="result-title-a"][href^="http"]',
                'div[data-testid="mainline"] article a[data-testid="result-title-a"][href^="http"]',
                'ol.react-results--main li article h2 a[href^="http"]:not([href*="duckduckgo.com"])',
                'div[data-type="instant-answer"] a[href^="http"]:not([href*="duckduckgo.com"])',
                'div.zci__result a[href^="http"]:not([href*="duckduckgo.com"])',
                'a[data-testid="result-extras-url-link"][href^="http"]:not([href*="duckduckgo.com"])',
                'div[data-result="true"] a.result__a[href^="http"]:not([href*="duckduckgo.com"])',
                'a.result__url[href^="http"]:not([href*="duckduckgo.com"])',
                'article[data-nrn] a[href^="http"]:not([href*="duckduckgo.com"])',
                'div.results a[href^="http"]:not([href*="duckduckgo.com"])',
                'div#links a[href^="http"]:not([href*="duckduckgo.com"])',
                'article span.result__url',
                'span.c-info__url[title^="http"]',
                'div.result__url[title^="http"]',
            ],
            "exclude_domains": ["duckduckgo.com", "duck.com", "start.duckduckgo.com"],
            "wait_for_selector": 'article[data-testid="result"], div[data-testid="mainline"], div[data-result="organic"]',
            "priority_selectors": [
                'article[data-result="organic"] h2 a[href^="http"]:not([href*="duckduckgo.com"])',
                'article[data-testid="result"] h2 a[data-testid="result-title-a"][href^="http"]',
                'h2 a[href^="http"]',
                'a[href^="http"][data-result]',
                'div[data-result] a',
                'article[data-result] a',
                'a[data-testid="result-title-a"]',
                'h2 a[data-result]',
                'div[data-result] h2 a',
                'a[href^="https"][data-result]',
                'div[data-nir] a',
                'div[data-result] a[href^="http"]',
                'h2.result__title a',
                'a.result__a',
                'div.result__body h2 a',
                'a[data-result-url]',
                'div[data-result-url] a',
                'h2[data-result] a',
                'a[rel="nofollow"][data-result]'
            ],
        },
        {
            "name": "Yandex",
            "enabled": SEARCH_ENGINES_ENABLED.get("Yandex", True),
            "url": f"https://yandex.com/search/?text={encoded_query}&lr=10262",
            "selectors": [
                'li[data-cid] div.Organic h2 a.Link[href^="http"]:not([href*="yandex"])',
                'div.serp-item div.OrganicTitle a.Link[href^="http"]:not([href*="yandex"])',
                'li.serp-item div.Organic-ContentWrapper a.link[href^="http"]:not([href*="yandex"])',
                'div.turbo-button a[href^="http"]:not([href*="yandex"])',
                'div.turbo-preview a[href^="http"]:not([href*="yandex"])',
                'div[data-cid] a[href^="http"][data-log-node]:not([href*="yandex"])',
                'div.Organic a[href^="http"]:not([href*="yandex"])',
                'div.serp-item a.organic__url[href^="http"]:not([href*="yandex"])',
                'div[data-counter] a[href^="http"]:not([href*="yandex"])',
                'div.organic__subtitle a[href^="http"]:not([href*="yandex"])',
                'div.serp-list a[href^="http"]:not([href*="yandex"])',
                'b-link a[href^="http"]:not([href*="yandex"])',
                'div.content__left a[href^="http"]:not([href*="yandex"])',
            ],
            "exclude_domains": ["yandex.com", "yandex.ru", "ya.ru", "yastatic.net", "yandex.st"],
            "wait_for_selector": 'div.serp-list, li[data-cid], div.content__left',
            "priority_selectors": [
                'li[data-cid] div.Organic h2 a.Link[href^="http"]:not([href*="yandex"])',
                'div.serp-item div.OrganicTitle a.Link[href^="http"]:not([href*="yandex"])',
                'h2 a[href^="http"]',
                'div.OrganicTitle a',
                'a.OrganicTitle-Link',
                'div[data-fast-name="organic"] a',
                'div.OrganicTitle a[href^="http"]',
                'h2.OrganicTitle a',
                'a.OrganicTitle-Link[href^="http"]',
                'div[data-fast-name="organic"] a[href^="http"]',
                'div.OrganicTitle-Link a',
                'h2.OrganicTitle-Link a',
                'div[data-cid] a[href^="http"]',
                'a[data-fast-name="organic"]',
                'div.Organic a[href^="http"]',
                'li.Organic a',
                'div.OrganicTitle a[target="_blank"]',
                'a.OrganicTitle[href^="https"]'
            ],
        },
        {
            "name": "Yahoo",
            "enabled": SEARCH_ENGINES_ENABLED.get("Yahoo", True),
            "url": f"https://search.yahoo.com/search?p={encoded_query}",
            "selectors": [
                'div#web ol li div.dd.algo h3.title a[href^="http"]:not([href*="yahoo.com"])',
                'div.searchCenterMiddle li div.compTitle h3 a[href^="http"]:not([href*="yahoo.com"])',
                'div[data-component="algo"] a.ac-algo[href^="http"]:not([href*="yahoo.com"])',
                'div#results div.algo h3 a[href^="http"]:not([href*="yahoo.com"])',
                'div.algo-sr a.fz-14[href^="http"]:not([href*="yahoo.com"])',
                'div.algo-sr a.ac-algo[href^="http"]:not([href*="yahoo.com"])',
                'div#right div.algo h3 a[href^="http"]:not([href*="yahoo.com"])',
                'div#sidebar div.algo h3 a[href^="http"]:not([href*="yahoo.com"])',
                'div.dd a[href^="http"]:not([href*="yahoo.com"])',
                'div.algo-sr a.ac-algo-fz[href^="http"]:not([href*="yahoo.com"])',
                'div.compTitle a[href^="http"]:not([href*="yahoo.com"])',
                'span.fz-15px',
                'div.compText a[href^="http"]:not([href*="yahoo.com"])',
                'div#main a[href^="http"]:not([href*="yahoo.com"])',
                'div#results a[href^="http"]:not([href*="yahoo.com"])',
                'div#mainline a[href^="http"]:not([href*="yahoo.com"])',
            ],
            "exclude_domains": ["yahoo.com", "search.yahoo.com", "yahoo.net"],
            "wait_for_selector": 'div#web, div.searchCenterMiddle, div#results',
            "priority_selectors": [
                'div#web ol li div.dd.algo h3.title a[href^="http"]:not([href*="yahoo.com"])',
                'div#results div.algo h3 a[href^="http"]:not([href*="yahoo.com"])',
            ],
        },
        {
            "name": "Brave",
            "enabled": SEARCH_ENGINES_ENABLED.get("Brave", True),
            "url": f"https://search.brave.com/search?q={encoded_query}&source=web",
            "selectors": [
                'div[data-type="web"] div.snippet a[href^="http"]:not([href*="brave.com"])',
                'div.fdb-container div.snippet-title a[href^="http"]:not([href*="brave.com"])',
                'div#results a.result-header[href^="http"]:not([href*="brave.com"])',
                'article[data-type="web"] a[href^="http"]:not([href*="brave.com"])',
                'div[data-result="web"] a[href^="http"]:not([href*="brave.com"])',
                'div.snippet__body a[href^="http"]:not([href*="brave.com"])',
                'div[data-type="infobox"] a[href^="http"]:not([href*="brave.com"])',
                'div.infobox a[href^="http"]:not([href*="brave.com"])',
               'div.card a[href^="http"]:not([href*="brave.com"])',
                'div.result-card a[href^="http"]:not([href*="brave.com"])',
                'div#results a[href^="http"]:not([href*="brave.com"])',
                'main a[href^="http"]:not([href*="brave.com"])',
            ],
            "exclude_domains": ["brave.com", "search.brave.com", "brave.net"],
            "wait_for_selector": 'div#results, div[data-type="web"], article[data-type="web"]',
            "priority_selectors": [
                'div[data-type="web"] div.snippet a[href^="http"]:not([href*="brave.com"])',
                'article[data-type="web"] a[href^="http"]:not([href*="brave.com"])',
            ],
        },
        {
            "name": "Ecosia",
            "enabled": SEARCH_ENGINES_ENABLED.get("Ecosia", True),
            "url": f"https://www.ecosia.org/search?q={encoded_query}",
            "selectors": [
                'section.mainline div.result a.result-url[href^="http"]:not([href*="ecosia.org"])',
                'div.result__title a[href^="http"]:not([href*="ecosia.org"])',
                'article.result a[href^="http"]:not([href*="ecosia.org"])',
                'div[data-testid="result"] a[href^="http"]:not([href*="ecosia.org"])',
                'article[data-result="web"] a[href^="http"]:not([href*="ecosia.org"])',
                'div.web-results a[href^="http"]:not([href*="ecosia.org"])',
                'div.ads-ad a[href^="http"]:not([href*="ecosia.org"])',
                'div.result--ad a[href^="http"]:not([href*="ecosia.org"])',
                'div.news-result a[href^="http"]:not([href*="ecosia.org"])',
                'div.image-result a[href^="http"]:not([href*="ecosia.org"])',
                'div.results a[href^="http"]:not([href*="ecosia.org"])',
                'main a[href^="http"]:not([href*="ecosia.org"])',
                'section a[href^="http"]:not([href*="ecosia.org"])',
                'div.result-url',
                'span.result-url',
            ],
            "exclude_domains": ["ecosia.org", "bing.com"],
            "wait_for_selector": 'section.mainline, div.result, div.web-results',
            "priority_selectors": [
                'section.mainline div.result a.result-url[href^="http"]:not([href*="ecosia.org"])',
                'div[data-testid="result"] a[href^="http"]:not([href*="ecosia.org"])',
                'div.result__title a[href^="http"]:not([href*="ecosia.org"])',
                'article.result a[href^="http"]:not([href*="ecosia.org"])',
                'div.web-results a[href^="http"]:not([href*="ecosia.org"])',
                'section.mainline a.result-url[href^="https"]:not([href*="ecosia.org"])',
                'div[data-testid="result"] a[href^="https"]:not([href*="ecosia.org"])',
                'div.result__title a[target="_blank"]:not([href*="ecosia.org"])',
                'article[data-result="web"] a[href^="http"]:not([href*="ecosia.org"])',
                'div.result-item a[href^="http"]:not([href*="ecosia.org"])',
                'h3.result__title a[href^="http"]:not([href*="ecosia.org"])',
                'a.result-url[target="_blank"]:not([href*="ecosia.org"])',
                'div[data-result] a[href^="http"]:not([href*="ecosia.org"])',
                'section a[href^="http"]:not([href*="ecosia.org"])'
            ],
        },
        {
            "name": "Startpage",
            "enabled": SEARCH_ENGINES_ENABLED.get("Startpage", True),
            "url": f"https://www.startpage.com/sp/search?query={encoded_query}",
            "selectors": [
                'section.w-gl div.w-gl__result a[href^="http"]:not([href*="startpage.com"])',
                'div.w-gl__result a.result-link[href^="http"]:not([href*="startpage.com"])',
                'div.result a[href^="http"]:not([href*="startpage.com"])',
                'article.search-result a[href^="http"]:not([href*="startpage.com"])',
                'div.search-result a[href^="http"]:not([href*="startpage.com"])',
                'main a[href^="http"]:not([href*="startpage.com"])',
                'div#results a[href^="http"]:not([href*="startpage.com"])',
            ],
            "exclude_domains": ["startpage.com", "startmail.com"],
            "wait_for_selector": 'section.w-gl, div.w-gl__result, div#results',
            "priority_selectors": [
                'section.w-gl div.w-gl__result a[href^="http"]:not([href*="startpage.com"])',
                'div.w-gl__result a.result-link[href^="http"]:not([href*="startpage.com"])',
                'div.w-gl__result a[href^="https"]:not([href*="startpage.com"])',
                'article.search-result a[href^="http"]:not([href*="startpage.com"])',
                'div.search-result a[href^="http"]:not([href*="startpage.com"])',
                'section.w-gl a[href^="http"]:not([href*="startpage.com"])',
                'div.w-gl__result a[target="_blank"]:not([href*="startpage.com"])',
                'div#results a[href^="http"]:not([href*="startpage.com"])',
                'main a[href^="http"]:not([href*="startpage.com"])',
                'div.search-result a[target="_blank"]:not([href*="startpage.com"])',
                'article.search-result a[href^="https"]:not([href*="startpage.com"])',
                'a.result-link[target="_blank"]:not([href*="startpage.com"])'
            ],
        },
    ]
    
    # فیلتر کردن فقط موتورهای فعال شده
    return [engine for engine in all_engines if engine.get("enabled", False)]

# ==================== تنظیمات حالت‌های اجرا ====================
MODES = {
    "deep_crawl": True,  # کرال عمیق (باز کردن لینک‌های داخلی)
}

# ==================== تنظیمات کرال عمیق ====================
DEEP_CRAWL_MAX_LINKS = 5
DEEP_CRAWL_MAX_DEPTH = 2

def get_deep_crawl_selectors(target_domain: str) -> list:
    """
    انتخابگرهای کرال عمیق را بر اساس دامنه هدف برمی‌گرداند.
    """
    if not target_domain:
        return []

    return [
        f'a[href*="{target_domain}"]',
        'article a[href^="/"]',
        'nav a[href^="/"]',
        'main a[href^="/"]',
        'div.content a[href^="/"]',
        'a.internal-link',
        'a[href^="/"]:not([href^="//"])',
    ]

# ==================== تنظیمات پیشرفته ====================
RANDOMNESS_FACTOR = 0.3

# تنظیمات تعاملات انسانی
MOUSE_MOVEMENTS_RANGE = (3, 7)
CLICK_CHANCE = 0.7
BACK_TO_TOP_CHANCE = 0.3

# تنظیمات لاگینگ
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
SAVE_SCREENSHOTS = os.getenv('SAVE_SCREENSHOTS', 'true').lower() == 'true'
SCREENSHOT_DIR = os.getenv('SCREENSHOT_DIR', 'screenshots')

# تنظیمات امنیتی
CAPTCHA_MAX_WAIT = int(os.getenv('CAPTCHA_MAX_WAIT', '120'))

# ==================== User-Agent سفارشی ====================
CUSTOM_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36",
]

# ==================== تنظیمات شبیه‌سازی انسان ====================
HUMAN_BEHAVIOR = {
    "typing_speed_range": (0.1, 0.3),
    "read_speed_wpm": (200, 300),
    "attention_span": (30, 90),
    "scroll_pattern": "natural",
}

# ==================== تنظیمات fallback ====================
FALLBACK_STRATEGIES = {
    "extract_from_text": True,          # استخراج URL از متن صفحه
    "use_navigation_timing": True,      # استفاده از Navigation Timing API
    "check_redirects": True,            # بررسی ریدایرکت‌ها
    "parse_json_ld": True,              # پارس کردن JSON-LD برای URL
    "extract_from_meta": True,          # استخراج از متا تگ‌ها
    "use_regex_patterns": True,         # استفاده از الگوهای regex پیشرفته
    "extract_from_scripts": True,       # استخراج از اسکریپت‌ها
    "try_alternative_selectors": True,  # تلاش با انتخابگرهای جایگزین
    "use_aria_labels": True,            # استفاده از برچسب‌های ARIA
    "extract_from_images": True         # استخراج از تصاویر و alt text
}

# ==================== لیست دستگاه‌های شبیه‌سازی ====================
DEVICES = [
    "iPhone 15 Pro",
    "iPhone 16",
    "iPhone 12 Pro",
    "iPhone 12",
    "Pixel 7",
    "Galaxy S22 Ultra",
    "Galaxy S24 Ultra"
    "Galaxy S25"
]

# ==================== اهداف SEO (TARGETS) - اینجا تغییر دهید ====================
TARGETS = [
    {
        "TARGET_DOMAIN": "gcorp.cc",  # دامنه هدف (مثال: x.ai برای تست)
        "QUERIES": [
          "ویدا شکیبا"
        ],
        "SEARCH": False,  # فعال کردن جستجو
        "DIRECT_VISIT_URLS": [
            "https://gcorp.cc",
            "https://gcorp.cc/articles",
            "https://gcorp.cc/?page=2",
            "https://gcorp.cc/?page=3",
        ]
    },
    # مثال دوم - اضافه کنید:
    # {
    #     "TARGET_DOMAIN": "yourdomain.com",
    #     "QUERIES": ["your keyword1", "keyword2"],
    #     "SEARCH": True,
    #     "DIRECT_VISIT_URLS": ["https://yourdomain.com"]
    # }
]

# ==================== تنظیمات تاخیرهای انسانی ====================
BETWEEN_ENGINES_DELAY = (20, 40)  # تاخیر بین موتورهای جستجو (ثانیه)
BETWEEN_PAGES_DELAY = (10, 25)    # تاخیر بین صفحات (ثانیه)

# ==================== فعال‌سازی موتورهای جستجو ====================
SEARCH_ENGINES_ENABLED = {
    "Google": True,
    "Bing": True,
    "DuckDuckGo": True,
    "Yandex": True,
    "Yahoo": True,
    "Brave": True,
    "Ecosia": True,
    "Startpage": True
}

# ==================== راه‌اندازی مدیر پروکسی (فقط از CSV) ====================
# حذف proxy_config_file - فقط از CSV استفاده می‌کنیم
proxy_manager = ProxyManager()

# فراخوانی بارگذاری فقط از CSV
load_proxies_from_csv_advanced()

# تابع برای پروکسی‌های فعال (sync برای سادگی، await در main.py حذف شود یا async شود)
def get_active_proxies_advanced():
    """دریافت پروکسی‌های فعال"""
    return proxy_manager.active_proxies[:]

# ==================== تابع‌های اضافی برای کامل‌تر کردن ====================

def is_same_domain(url: str, target_domain: str) -> bool:
    """بررسی اینکه آیا URL متعلق به دامنه هدف است"""
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    return parsed_url.netloc.lower().endswith(target_domain.lower())

def human_delay(min_delay: float, max_delay: float) -> float:
    """ایجاد تاخیر انسانی تصادفی"""
    return random.uniform(min_delay, max_delay)

# ==================== تنظیمات اضافی ====================
MAX_DEVICES_PER_TARGET = 3  # حداکثر دستگاه برای هر هدف
USE_CUSTOM_USER_AGENTS = True  # استفاده از user-agent سفارشی
ENABLE_TRACING = True  # فعال کردن tracing برای دیباگ

if __name__ == "__main__":
    # تست بارگذاری پروکسی‌ها فقط از CSV
    print("🔄 در حال بارگذاری پروکسی‌ها فقط از CSV...")
    
    # بارگذاری از CSV
    csv_proxies = load_proxies_from_csv_advanced()
    print(f"📊 تعداد پروکسی‌های بارگذاری شده از CSV: {len(csv_proxies)}")
    
    # تست ProxyManager
    print("\n🔄 در حال تست ProxyManager...")
    manager = ProxyManager()
    print(f"📊 تعداد پروکسی‌ها در ProxyManager: {len(manager.proxies)}")
    
    # نمایش چند نمونه
    if csv_proxies:
        print("\n🔍 نمونه پروکسی‌ها:")
        for i, proxy in enumerate(csv_proxies[:3], 1):
            print(f"  {i}. {proxy.url} ({proxy.country}, {proxy.latency}ms, {proxy.protocol})")
    
    print("\n✅ تست بارگذاری پروکسی‌ها فقط از CSV با موفقیت انجام شد!")