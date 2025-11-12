# -*- coding: utf-8 -*-
"""
مدیریت پروکسی - بدون تغییر
"""
import asyncio
import logging
from typing import List, Optional, Any

from .proxy_config_model import ProxyConfig, ProxyType
from .proxy_utils import _parse_proxy_string
from core import logger

try:
    import requests
except Exception:
    requests = None

_LOG = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        self.proxies: List[ProxyConfig] = []
        self.active_proxies: List[ProxyConfig] = []

    def add_proxy(self, proxy: Any) -> bool:
        """افزودن یک پروکسی"""
        if isinstance(proxy, ProxyConfig):
            self.proxies.append(proxy)
            if proxy.is_active:
                self.active_proxies.append(proxy)
            return True
        if isinstance(proxy, str):
            pc = _parse_proxy_string(proxy)
            if pc:
                self.proxies.append(pc)
                if pc.is_active:
                    self.active_proxies.append(pc)
                return True
        return False

    def add_manual_proxies(self, proxies: List[Any]) -> int:
        """افزودن لیست پروکسی‌ها"""
        added = 0
        for p in proxies:
            try:
                if self.add_proxy(p):
                    added += 1
            except Exception:
                continue
        return added

    add_proxies = add_manual_proxies

    def get_active_proxies(self) -> List[ProxyConfig]:
        """دریافت پروکسی‌های فعال"""
        return list(self.active_proxies)

    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """پروکسی تصادفی"""
        import random
        if not self.active_proxies:
            return None
        return random.choice(self.active_proxies)

    def mark_failed(self, url_or_obj: Any):
        """علامت‌گذاری ناموفق"""
        for p in self.proxies:
            try:
                if isinstance(p, ProxyConfig):
                    if p.url == getattr(url_or_obj, "url", url_or_obj) or p.ip == getattr(url_or_obj, "ip", None):
                        p.mark_failed()
                        if not p.is_active and p in self.active_proxies:
                            self.active_proxies.remove(p)
                        break
            except Exception:
                continue

    def mark_success(self, url_or_obj: Any):
        """علامت‌گذاری موفق"""
        for p in self.proxies:
            try:
                if isinstance(p, ProxyConfig):
                    if p.url == getattr(url_or_obj, "url", url_or_obj) or p.ip == getattr(url_or_obj, "ip", None):
                        p.mark_success()
                        if p.is_active and p not in self.active_proxies:
                            self.active_proxies.append(p)
                        break
            except Exception:
                continue

    async def run_proxy_validation(self, concurrency: int = 50, test_url: str = "http://httpbin.org/ip", timeout: int = 6):
        """بررسی پروکسی‌ها با نتایج تفصیلی"""
        if requests is None:
            _LOG.warning("requests module not available")
            return {}

        targets = list(self.proxies)
        if not targets:
            _LOG.info("No proxies to validate")
            return {}

        loop = asyncio.get_running_loop()
        sem = asyncio.Semaphore(concurrency)
        
        results = {
            'working': [],
            'failed': [],
            'timeout': [],
            'errors': []
        }

        async def _check(pc: ProxyConfig):
            async with sem:
                return await loop.run_in_executor(None, _sync_check, pc, test_url, timeout)

        def _sync_check(pc: ProxyConfig, test_url: str, timeout: int) -> tuple:
            try:
                proxy_url = f"{pc.protocol.value}://{pc.ip}:{pc.port}"
                proxies = {"http": proxy_url, "https": proxy_url}
                resp = requests.get(test_url, proxies=proxies, timeout=timeout)
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        return ('working', pc, {
                            'proxy': pc.url,
                            'time': resp.elapsed.total_seconds() * 1000,
                            'ip': data.get('origin', 'Unknown')
                        })
                    except:
                        return ('working', pc, {
                            'proxy': pc.url,
                            'time': resp.elapsed.total_seconds() * 1000,
                            'ip': 'Unknown'
                        })
                else:
                    return ('failed', pc, {
                        'proxy': pc.url,
                        'error': f"Status {resp.status_code}"
                    })
            except asyncio.TimeoutError:
                return ('timeout', pc, pc.url)
            except Exception as e:
                return ('error', pc, {
                    'proxy': pc.url,
                    'error': str(e)[:100]
                })

        tasks = [asyncio.create_task(_check(pc)) for pc in targets]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # معالجه نتایج
        for response in responses:
            if isinstance(response, Exception):
                continue
            
            status, pc, data = response
            
            if status == 'working':
                results['working'].append(data)
                if pc not in self.active_proxies:
                    self.active_proxies.append(pc)
            elif status == 'failed':
                results['failed'].append(data)
                pc.mark_failed()
                if pc in self.active_proxies:
                    self.active_proxies.remove(pc)
            elif status == 'timeout':
                results['timeout'].append(data)
                pc.mark_failed()
                if pc in self.active_proxies:
                    self.active_proxies.remove(pc)
            elif status == 'error':
                results['errors'].append(data)
                pc.mark_failed()
                if pc in self.active_proxies:
                    self.active_proxies.remove(pc)

        _LOG.info(f"Proxy validation complete: {len(results['working'])}/{len(targets)} working")
        return results

# Instance
proxy_manager = ProxyManager()

# Exports
__all__ = ["ProxyManager", "proxy_manager", "ProxyConfig"]
ProxyConfig = ProxyConfig  # alias برای اهداف backward compatibility