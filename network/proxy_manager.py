# -*- coding: utf-8 -*-
"""
network.proxy_manager: سازگار با main.py و proxy_checker.py

ارائه متدهای:
- load_proxies_from_csv(path)
- add_manual_proxies(list[str|ProxyConfig]) -> int
- add_proxies(...)
- add_proxy(ProxyConfig)
- get_active_proxies() -> List[ProxyConfig]
- run_proxy_validation(concurrency=50)  # async
- get_random_proxy()
- mark_failed(url) / mark_success(url)
"""
from typing import List, Optional, Any
import asyncio
import concurrent.futures
import csv
import os
import logging
import random
import time
from urllib.parse import urlparse

# استفاده از کلاس مدل از config.proxy_config
from config.proxy_config import ProxyConfig as ConfProxyConfig, ProxyType
from core import logger

try:
    import requests
except Exception:
    requests = None

_LOG = logging.getLogger(__name__)

def _parse_proxy_string(s: str) -> Optional[ConfProxyConfig]:
    if not s:
        return None
    s = s.strip().strip('"').strip("'")
    scheme = None
    hostport = s
    if '://' in s:
        scheme, hostport = s.split('://', 1)
    if ':' in hostport:
        host, port = hostport.rsplit(':', 1)
    else:
        host, port = hostport, 0
    # normalize protocol
    proto = ProxyType.HTTP
    if scheme:
        try:
            proto = ProxyType(scheme.lower())
        except Exception:
            try:
                proto = ProxyType[scheme.upper()]
            except Exception:
                proto = ProxyType.HTTP
    try:
        pc = ConfProxyConfig(url=s, ip=host, port=int(port or 0), protocol=proto)
        return pc
    except Exception:
        return None

class ProxyManager:
    def __init__(self):
        # internal storage: list of ProxyConfig or raw strings (converted where possible)
        self.proxies: List[Any] = []
        self.active_proxies: List[Any] = []

    # متدهای افزودن
    def add_proxy(self, proxy: Any) -> bool:
        """افزودن یک ProxyConfig یا رشته. برگشت True اگر اضافه شد."""
        if isinstance(proxy, ConfProxyConfig):
            self.proxies.append(proxy)
            if proxy.is_active:
                self.active_proxies.append(proxy)
            return True
        # اگر رشته، تلاش برای تبدیل
        if isinstance(proxy, str):
            pc = _parse_proxy_string(proxy)
            if pc:
                self.proxies.append(pc)
                if pc.is_active:
                    self.active_proxies.append(pc)
                return True
            # اگر نتوان تبدیل کرد، نگه دار رشته (تا fallbackها آن را تبدیل کنند)
            self.proxies.append(proxy)
            self.active_proxies.append(proxy)
            return True
        return False

    def add_manual_proxies(self, proxies: List[Any]) -> int:
        """افزودن لیستی از پروکسی‌ها (رشته یا ProxyConfig). برمی‌گرداند تعداد افزوده‌شده."""
        added = 0
        for p in proxies:
            try:
                if self.add_proxy(p):
                    added += 1
            except Exception:
                continue
        return added

    # آلیاس خواناتر
    add_proxies = add_manual_proxies

    # بارگذاری از CSV ساده (در صورت نبود loader دیگر)
    def load_proxies_from_csv(self, path: Optional[str] = None) -> List[Any]:
        if not path:
            # مسیر پیش‌فرض از کانفیگ
            path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "proxies-export.csv")
        result = []
        if not os.path.exists(path):
            _LOG.debug(f"CSV پروکسی یافت نشد: {path}")
            return result
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                # تلاش برای DictReader سپس fallback به reader ساده
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    cell = row[0] if len(row) >= 1 else None
                    if cell:
                        result.append(cell.strip())
            # اضافه کردن به manager
            self.add_manual_proxies(result)
            _LOG.info(f"✅ {len(result)} پروکسی از CSV بارگذاری شد (network.proxy_manager)")
        except Exception as e:
            _LOG.error(f"خطا در بارگذاری CSV در network.proxy_manager: {e}", exc_info=True)
        return result

    # خواندن پروکسی‌های فعال (برگردان لیست ProxyConfig یا رشته)
    def get_active_proxies(self) -> List[Any]:
        return list(self.active_proxies)

    def get_random_proxy(self) -> Optional[Any]:
        if not self.active_proxies:
            return None
        return random.choice(self.active_proxies)

    def mark_failed(self, url_or_obj: Any):
        # اگر آیتم ProxyConfig است
        for p in self.proxies:
            try:
                if isinstance(p, ConfProxyConfig) and (p.url == getattr(url_or_obj, "url", url_or_obj) or p.ip == getattr(url_or_obj, "ip", None)):
                    p.failure_count += 1
                    p.success_rate = max(0.0, p.success_rate - 0.1)
                    if p.failure_count >= 3:
                        p.is_active = False
                        if p in self.active_proxies:
                            self.active_proxies.remove(p)
                    break
            except Exception:
                continue

    def mark_success(self, url_or_obj: Any):
        for p in self.proxies:
            try:
                if isinstance(p, ConfProxyConfig) and (p.url == getattr(url_or_obj, "url", url_or_obj) or p.ip == getattr(url_or_obj, "ip", None)):
                    p.success_rate = min(1.0, p.success_rate + 0.05)
                    p.last_used = datetime_now_iso()
                    if p.is_active and p not in self.active_proxies:
                        self.active_proxies.append(p)
                    break
            except Exception:
                continue

    async def run_proxy_validation(self, concurrency: int = 50, test_url: str = "http://httpbin.org/ip", timeout: int = 6):
        """Async validation: از thread pool برای اجرای requests استفاده می‌کند."""
        if requests is None:
            _LOG.warning("کتابخانه requests موجود نیست؛ بررسی پروکسی نادیده گرفته شد.")
            return

        # ساخت لیست اهداف تستی (کسانی که دارای ip/port یا رشته هستند)
        targets = []
        for p in list(self.proxies):
            if isinstance(p, ConfProxyConfig):
                targets.append(p)
            elif isinstance(p, str):
                pc = _parse_proxy_string(p)
                if pc:
                    targets.append(pc)
                else:
                    # رشته نامعلوم را نادیده بگیر
                    continue
            else:
                continue

        if not targets:
            _LOG.info("هیچ پروکسی معتبری برای بررسی یافت نشد.")
            return

        loop = asyncio.get_running_loop()
        sem = asyncio.Semaphore(concurrency)
        added_active = []

        async def _check(pc: ConfProxyConfig):
            async with sem:
                return await loop.run_in_executor(None, _sync_check, pc, test_url, timeout)

        def _sync_check(pc: ConfProxyConfig, test_url: str, timeout: int) -> bool:
            try:
                proxy_url = f"{pc.protocol.value}://{pc.ip}:{pc.port}" if pc.port else f"{pc.protocol.value}://{pc.ip}"
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
                resp = requests.get(test_url, proxies=proxies, timeout=timeout)
                ok = resp.status_code == 200
                return ok
            except Exception:
                return False

        tasks = [asyncio.create_task(_check(pc)) for pc in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # بروزرسانی وضعیت‌ها
        valid_count = 0
        for pc, res in zip(targets, results):
            ok = False
            if isinstance(res, Exception):
                ok = False
            else:
                ok = bool(res)
            if ok:
                valid_count += 1
                # اگر نسخه اصلی لیست شامل رشته بود، جایگزین کن با شیء
                # و به active_proxies اضافه کن یک‌بار
                try:
                    # پیدا کن عضو اولیه در self.proxies و جایگزین کن
                    for i, orig in enumerate(self.proxies):
                        if isinstance(orig, str) and orig.strip() == pc.url:
                            self.proxies[i] = pc
                            break
                    if pc not in self.active_proxies:
                        self.active_proxies.append(pc)
                except Exception:
                    pass
            else:
                # ناموفق -> علامت‌گذاری (failure_count و حذف از active)
                try:
                    for stored in list(self.proxies):
                        if isinstance(stored, ConfProxyConfig) and stored.url == pc.url:
                            stored.failure_count += 1
                            if stored.failure_count >= 3 and stored in self.active_proxies:
                                self.active_proxies.remove(stored)
                except Exception:
                    pass

        _LOG.info(f"Proxy validation done: {valid_count}/{len(targets)} valid")

# helper
def datetime_now_iso():
    from datetime import datetime
    return datetime.now().isoformat()

# instance
proxy_manager = ProxyManager()

# ------ اضافه‌شده: صادر کردن نام ProxyConfig از این ماژول ------
# تا import از "from network.proxy_manager import ProxyConfig" کار کند
ProxyConfig = ConfProxyConfig

# صریح کردن صادرات ماژول
__all__ = ["ProxyManager", "proxy_manager", "ProxyConfig", "ProxyType"]
# ------ پایان اضافه‌شده ------