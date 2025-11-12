# -*- coding: utf-8 -*-
from typing import List, Dict, Optional

# از فایل جدید ایمپورت می‌کنیم
from proxy_manager import ProxyConfig
from core.logger import logger

def validate_proxy_format(proxy_url: str) -> bool:
    """
    این تابع اکنون می‌تواند به proxy_manager منتقل شود، اما برای سازگاری نگه داشته شده است.
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(proxy_url)
        if parsed.scheme not in ['http', 'https', 'socks4', 'socks5']:
            return False
        if not parsed.hostname or not parsed.port:
            return False
        if not (1 <= parsed.port <= 65535):
            return False
        return True
    except Exception:
        return False

def filter_proxies_by_criteria(proxies: List[ProxyConfig], 
                               max_latency: float = 5.0, # تغییر به ثانیه
                               min_success_rate: float = 0.7,
                               countries: List[str] = None) -> List[ProxyConfig]:
    """
    پروکسی‌ها را بر اساس معیارهای داده شده فیلتر می‌کند.
    """
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
    """
    (به‌روز شده) - یک آبجکت ProxyConfig از ردیف CSV ایجاد می‌کند.
    """
    try:
        ip = row.get('IP', '').strip().strip('"')
        port = row.get('Port', '').strip().strip('"')
        protocol_str = row.get('Protocol', 'HTTP').strip().strip('"')
        country = row.get('Country', 'Unknown').strip().strip('"')
        latency_str = row.get('Latency', '0').strip().strip('"')
        
        if not ip or not port:
            return None
        
        protocol_map = {
            'HTTP': 'http',
            'HTTPS': 'https', 
            'SOCKS4': 'socks4',
            'SOCKS5': 'socks5'
        }
        
        protocol = protocol_map.get(protocol_str.upper(), 'http')
        port_int = int(port)
        
        # تبدیل Latency از 'ms' به ثانیه اگر لازم باشد
        try:
            if 'ms' in latency_str:
                latency_float = float(latency_str.replace(' ms', '')) / 1000.0
            else:
                latency_float = float(latency_str)
        except ValueError:
            latency_float = float('inf') # اگر مقدار نامعتبر بود
        
        proxy_url = f"{protocol}://{ip}:{port_int}"
        
        return ProxyConfig(
            url=proxy_url,
            ip=ip,
            port=port_int,
            protocol=protocol,
            country=country,
            latency=latency_float, # استفاده از مقدار float
            is_active=True # فرض اولیه بر فعال بودن تا زمان بررسی
        )
    except Exception as e:
        logger.error(f"خطا در ایجاد پروکسی از CSV: {e} - ردیف: {row}")
        return None