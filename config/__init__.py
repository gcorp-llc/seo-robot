"""
مقادیر تنظیمات اصلی پروژه
"""

from .targets import TARGETS
from .proxy_config import MANUAL_PROXIES

# سعی برای وارد کردن از general_settings
try:
    from .general_settings import DEVICES
except ImportError:
    DEVICES = []

# تعریف USE_PROXY_ROTATION اگر موجود نبود
try:
    from .general_settings import USE_PROXY_ROTATION
except ImportError:
    USE_PROXY_ROTATION = True  # مقدار پیش‌فرض

# ایمپورت مدل‌های پروکسی از network
from network.proxy_config_model import ProxyConfig, ProxyType
from network.proxy_manager import proxy_manager

__all__ = [
    'TARGETS',
    'USE_PROXY_ROTATION',
    'DEVICES',
    'MANUAL_PROXIES',
    'ProxyConfig',
    'ProxyType',
    'proxy_manager',
]