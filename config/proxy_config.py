from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import random
import logging
import os
import inspect

# مسیر ریشه پروژه (پوشه حاوی این فایل‌ها)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# افزودن تنظیمات بارگذاری پروکسی (قابل تغییر توسط کاربر/محیط)
# مقدار پیش‌فرض حالا به فایل proxies-export.csv در روت پروژه اشاره می‌کند
PROXY_CSV_FILE: str = os.path.join(PROJECT_ROOT, 'proxies-export.csv')
PROXY_API_URL: Optional[str] = None  # مثال: 'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http'
MANUAL_PROXIES: List[str] = [
    'http://1.52.198.150:16000',
    "118.174.115.252:8080",
    "62.60.236.119:3128",
]       # مثال: ['http://1.2.3.4:8080']

class ProxyType(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

@dataclass
class ProxyConfig:
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
        # نرمال‌سازی ایمن protocol
        if isinstance(self.protocol, str):
            s = self.protocol.strip().lower()
            # حذف احتمالی "://" یا ":" که ممکن است در CSV آمده باشد
            if s.endswith('://'):
                s = s[:-3]
            if s.endswith(':'):
                s = s[:-1]
            # اگر مقدار سازگار بود، مقدار Enum را تنظیم کن؛ در غیر این صورت پیش‌فرض HTTP
            try:
                self.protocol = ProxyType(s)
            except Exception:
                # تلاش برای تطبیق با نام اعضا (در صورت ارسال 'HTTP' یا مشابه)
                try:
                    self.protocol = ProxyType[s.upper()]
                except Exception:
                    self.protocol = ProxyType.HTTP
        # پورت و latency را تبدیل کن
        if isinstance(self.port, str):
            try:
                self.port = int(self.port)
            except Exception:
                self.port = 0
        if isinstance(self.latency, str):
            try:
                self.latency = int(self.latency.replace(' ms', '').strip())
            except Exception:
                self.latency = 0

    def to_dict(self) -> Dict[str, Any]:
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
        return cls(**data)

class ProxyManager:
    def __init__(self):
        # حذف بارگذاری خودکار از __init__ تا کنترلی‌تر باشد
        self.proxies: List[ProxyConfig] = []
        self.active_proxies: List[ProxyConfig] = []
        # هنگام نیاز main.py یا هر ماژول دیگری صدا خواهد خورد:
        # await proxy_manager.load_proxies_from_csv(PROXY_CSV_FILE) یا proxy_manager.load_proxies_from_csv()

    def add_proxy(self, proxy: ProxyConfig):
        self.proxies.append(proxy)
        if proxy.is_active:
            self.active_proxies.append(proxy)
    
    def remove_proxy(self, url: str):
        self.proxies = [p for p in self.proxies if p.url != url]
        self.active_proxies = [p for p in self.active_proxies if p.url != url]
    
    def mark_failed(self, url: str):
        for proxy in self.proxies:
            if proxy.url == url:
                proxy.failure_count += 1
                proxy.success_rate = max(0.0, proxy.success_rate - 0.1)
                if proxy.failure_count >= 3:
                    proxy.is_active = False
                    self.active_proxies = [p for p in self.active_proxies if p.url != url]
                break
    
    def mark_success(self, url: str):
        for proxy in self.proxies:
            if proxy.url == url:
                proxy.success_rate = min(1.0, proxy.success_rate + 0.05)
                proxy.last_used = self._get_current_time()
                break
    
    def get_best_proxy(self) -> Optional[ProxyConfig]:
        if not self.active_proxies:
            return None
        sorted_proxies = sorted(
            self.active_proxies,
            key=lambda p: (p.success_rate, -p.latency, p.last_used or ''),
            reverse=True
        )
        top_proxies = sorted_proxies[:5]
        return random.choice(top_proxies) if top_proxies else None
    
    def get_random_proxy(self) -> Optional[ProxyConfig]:
        return random.choice(self.active_proxies) if self.active_proxies else None
    
    def get_proxy_by_country(self, country: str) -> Optional[ProxyConfig]:
        country_proxies = [p for p in self.active_proxies if p.country.lower() == country.lower()]
        return random.choice(country_proxies) if country_proxies else None
    
    def get_proxy_by_latency(self, max_latency: int) -> Optional[ProxyConfig]:
        fast_proxies = [p for p in self.active_proxies if p.latency <= max_latency]
        return random.choice(fast_proxies) if fast_proxies else None
    
    def get_all_proxy_urls(self) -> List[str]:
        return [p.url for p in self.proxies]
    
    def get_active_proxy_urls(self) -> List[str]:
        return [p.url for p in self.active_proxies]
    
    def load_proxies_from_csv(self, path: Optional[str] = None):
        """
        Load proxies using an internal loader if available.
        If load_proxies_from_csv_advanced accepts a path, pass it.
        Cache results in module-global _loaded_proxies_from_csv to avoid re-parsing.
        """
        global _loaded_proxies_from_csv
        _loaded_proxies_from_csv = globals().get('_loaded_proxies_from_csv', None)

        # Use provided path or default from config
        if not path:
            path = PROXY_CSV_FILE

        try:
            from .proxy_loader import load_proxies_from_csv_advanced
            # اگر کش وجود دارد و مقدار معتبر است از آن استفاده کن
            if _loaded_proxies_from_csv:
                proxies = _loaded_proxies_from_csv
            else:
                # بررسی سیگنچر تابع loader برای دیدن اینکه path می‌پذیرد یا خیر
                try:
                    sig = inspect.signature(load_proxies_from_csv_advanced)
                    if len(sig.parameters) == 0:
                        proxies = load_proxies_from_csv_advanced()
                    else:
                        proxies = load_proxies_from_csv_advanced(path)
                except (ValueError, TypeError):
                    # اگر نتوانستیم سیگنچر را بدست آوریم، تلاش با هر دو حالت
                    try:
                        proxies = load_proxies_from_csv_advanced(path)
                    except TypeError:
                        proxies = load_proxies_from_csv_advanced()
                _loaded_proxies_from_csv = proxies
            # اضافه کردن پروکسی‌ها (منتظر اشیاء یا رشته‌های نرمال‌شده)
            for proxy in proxies:
                # اگر proxy یک dict باشد سعی در تبدیل به ProxyConfig کن
                if isinstance(proxy, dict):
                    try:
                        pc = ProxyConfig.from_dict(proxy)
                        self.add_proxy(pc)
                        continue
                    except Exception:
                        pass
                # اگر proxy شیء ProxyConfig است، مستقیم اضافه کن
                if isinstance(proxy, ProxyConfig):
                    self.add_proxy(proxy)
                else:
                    # رشته یا دیگران را نگه دار (مستقیماً الحاق می‌کنیم؛ callers بعدا می‌توانند تبدیل کنند)
                    try:
                        self.proxies.append(proxy)
                        # رشته‌ها را به active_proxies هم اضافه کن (فرض فعال)
                        self.active_proxies.append(proxy)
                    except Exception:
                        continue
            logging.info(f"✅ {len(proxies)} پروکسی از CSV بارگذاری شد")
        except Exception as e:
            logging.error(f"خطا در بارگذاری پیکربندی پروکسی از CSV: {e}")
            # در حالت خطا، لیست‌ها را خالی کن اما اجازه بده caller مجدداً تلاش کند
            self.proxies = []
            self.active_proxies = []
    
    def _get_current_time(self) -> str:
        return datetime.now().isoformat()
    
    def __len__(self):
        return len(self.proxies)
    
    def __bool__(self):
        return bool(self.active_proxies)

proxy_manager = ProxyManager()