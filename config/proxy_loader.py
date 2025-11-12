import csv
from pathlib import Path
import logging
import os

from .proxy_config import ProxyConfig

PROXY_CONFIG = {
    'max_proxies': int(os.getenv('MAX_PROXIES', '0')),
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
}

PROXY_SECURITY = {
    'validate_ssl': True,
    'block_private_ips': True,
    'block_reserved_ips': True,
    'max_concurrent_requests': 10,
    'request_delay_range': (1, 3),
}

PROXY_CHECK_TIMEOUT = PROXY_CONFIG['proxy_check_timeout']
USE_PROXY_ROTATION = PROXY_CONFIG['use_proxy_rotation']
INCLUDE_NO_PROXY = PROXY_CONFIG['include_no_proxy']
MAX_RETRIES_PER_PROXY = PROXY_CONFIG['max_retries_per_proxy']

def validate_proxy_format(proxy_url: str) -> bool:
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
                               max_latency: int = 500,
                               min_success_rate: float = 0.7,
                               countries: List[str] = None) -> List[ProxyConfig]:
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

def load_proxies_from_csv_advanced(csv_file: str = "proxies-export.csv", 
                                   max_proxies: int = 0,
                                   min_latency: int = 0,
                                   max_latency: int = 500,
                                   preferred_countries: List[str] = None) -> List[ProxyConfig]:
    proxies = []
    csv_path = Path(csv_file)
    
    if not csv_path.exists():
        logging.error(f"فایل {csv_file} یافت نشد.")
        return proxies
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                proxy = create_proxy_from_csv_row(row)
                
                if proxy and validate_proxy_format(proxy.url):
                    if min_latency <= proxy.latency <= max_latency:
                        if preferred_countries:
                            if proxy.country in preferred_countries:
                                proxies.append(proxy)
                        else:
                            proxies.append(proxy)
                
                if max_proxies > 0 and len(proxies) >= max_proxies:
                    break
            
            proxies.sort(key=lambda p: (p.latency, -p.success_rate))
            
            logging.info(f"✅ {len(proxies)} پروکسی از فایل {csv_file} بارگذاری شد")
            
            global _loaded_proxies_from_csv
            _loaded_proxies_from_csv = proxies
            
            return proxies
        
    except Exception as e:
        logging.error(f"خطا در خواندن فایل CSV: {e}")
        return []

load_proxies_from_csv_advanced()

def get_active_proxies_advanced():
    from .proxy_config import proxy_manager  # import داخل تابع برای جلوگیری از circular
    return proxy_manager.active_proxies[:]