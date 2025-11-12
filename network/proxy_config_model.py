# -*- coding: utf-8 -*-
"""
مدل‌های داده پروکسی - استخراج شده از config/proxy_config.py
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

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
            if s.endswith('://'):
                s = s[:-3]
            if s.endswith(':'):
                s = s[:-1]
            try:
                self.protocol = ProxyType(s)
            except Exception:
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

    def mark_failed(self):
        """علامت‌گذاری ناموفق"""
        self.failure_count += 1
        self.success_rate = max(0.0, self.success_rate - 0.1)
        if self.failure_count >= 3:
            self.is_active = False

    def mark_success(self):
        """علامت‌گذاری موفق"""
        self.success_rate = min(1.0, self.success_rate + 0.05)
        self.last_used = datetime.now().isoformat()
        # فعال‌کردن مجدد اگر بود
        if self.failure_count > 0:
            self.failure_count = max(0, self.failure_count - 1)
        if self.failure_count < 3:
            self.is_active = True