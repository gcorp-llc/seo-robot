from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import random
import logging

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
        if isinstance(self.protocol, str):
            self.protocol = ProxyType(self.protocol.lower())
        if isinstance(self.port, str):
            self.port = int(self.port)
        if isinstance(self.latency, str):
            self.latency = int(self.latency.replace(' ms', ''))

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
        self.proxies: List[ProxyConfig] = []
        self.active_proxies: List[ProxyConfig] = []
        self.load_proxies_from_csv()
    
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
    
    def load_proxies_from_csv(self):
        try:
            from .proxy_loader import load_proxies_from_csv_advanced
            global _loaded_proxies_from_csv
            if '_loaded_proxies_from_csv' in globals() and _loaded_proxies_from_csv:
                proxies = _loaded_proxies_from_csv
            else:
                proxies = load_proxies_from_csv_advanced()
            for proxy in proxies:
                self.add_proxy(proxy)
            logging.info(f"✅ {len(proxies)} پروکسی از CSV بارگذاری شد")
        except Exception as e:
            logging.error(f"خطا در بارگذاری پیکربندی پروکسی از CSV: {e}")
            self.proxies = []
            self.active_proxies = []
    
    def _get_current_time(self) -> str:
        return datetime.now().isoformat()
    
    def __len__(self):
        return len(self.proxies)
    
    def __bool__(self):
        return bool(self.active_proxies)

proxy_manager = ProxyManager()