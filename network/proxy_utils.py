from typing import List, Dict, Optional

from config.proxy_config import ProxyConfig

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
        from core.logger import logger
        logger.error(f"خطا در ایجاد پروکسی از CSV: {e} - ردیف: {row}")
        return None