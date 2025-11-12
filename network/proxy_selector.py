"""
انتخاب هوشمند پروکسی (اختیاری)
"""
import random
from typing import Optional, List
from .proxy_config_model import ProxyConfig
from .proxy_manager import proxy_manager
from core.logger import logger

class ProxySelector:
    def __init__(self, proxy_manager):
        self.pm = proxy_manager

    def get_best_proxy(self) -> Optional[ProxyConfig]:
        """بهترین پروکسی بر اساس success_rate و latency"""
        logger.debug("در حال انتخاب بهترین پروکسی...")
        if not self.pm.active_proxies:
            return None
        sorted_proxies = sorted(
            self.pm.active_proxies,
            key=lambda p: (p.success_rate, -p.latency, p.last_used or ''),
            reverse=True
        )
        top_proxies = sorted_proxies[:5]
        return random.choice(top_proxies) if top_proxies else None

    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """پروکسی تصادفی"""
        return random.choice(self.pm.active_proxies) if self.pm.active_proxies else None

    def get_by_country(self, country: str) -> Optional[ProxyConfig]:
        """پروکسی برای کشور خاص"""
        matching = [p for p in self.pm.active_proxies if p.country.lower() == country.lower()]
        return random.choice(matching) if matching else None

    def get_by_latency(self, max_latency: int) -> Optional[ProxyConfig]:
        """پروکسی با latency کمتر از حد معین"""
        fast = [p for p in self.pm.active_proxies if p.latency <= max_latency]
        return random.choice(fast) if fast else None