# -*- coding: utf-8 -*-
import time
from dataclasses import dataclass
from urllib.parse import urlparse

# ایمپورت کردن logger از ریشه پروژه
from core.logger import logger

@dataclass
class ProxyConfig:
    """
    (منتقل شده) - یک دیتاکلاس برای نگهداری اطلاعات هر پروکسی.
    """
    url: str
    ip: str = ""
    port: int = 0
    protocol: str = "http"
    country: str = "Unknown"
    latency: float = float('inf')
    is_active: bool = False
    success_rate: float = 0.0
    failed_checks: int = 0
    success_checks: int = 0
    last_checked: float = 0.0

    def __post_init__(self):
        try:
            parsed = urlparse(self.url)
            self.protocol = parsed.scheme or "http"
            self.ip = parsed.hostname or ""
            self.port = parsed.port or 0
        except Exception:
            logger.warning(f"فرمت URL پروکسی نامعتبر: {self.url}")
            self.url = "" 

    def mark_success(self, latency: float):
        self.is_active = True
        self.latency = latency
        self.success_checks += 1
        self.last_checked = time.time()
        self._update_success_rate()

    def mark_failed(self):
        self.is_active = False
        self.latency = float('inf')
        self.failed_checks += 1
        self.last_checked = time.time()
        self._update_success_rate()

    def _update_success_rate(self):
        total_checks = self.success_checks + self.failed_checks
        if total_checks > 0:
            self.success_rate = self.success_checks / total_checks

    def __hash__(self):
        return hash(self.url)