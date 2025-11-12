# -*- coding: utf-8 -*-
"""
ابزارهای کمکی پارس پروکسی - منتقل شده از روت
"""
from typing import Optional
from .proxy_config_model import ProxyConfig, ProxyType

def _parse_proxy_string(s: str) -> Optional[ProxyConfig]:
    """تبدیل رشته پروکسی به ProxyConfig"""
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
        pc = ProxyConfig(url=s, ip=host, port=int(port or 0), protocol=proto)
        return pc
    except Exception:
        return None

def create_proxy_from_csv_row(row):
    """تبدیل ردیف CSV به رشته پروکسی"""
    try:
        if isinstance(row, dict):
            for key in ('proxy', 'address', 'ip', 'host'):
                if key in row and row[key]:
                    return str(row[key]).strip()
        if isinstance(row, (list, tuple)):
            if len(row) >= 1:
                return str(row[0]).strip()
        return str(row).strip() if row else None
    except Exception:
        return None