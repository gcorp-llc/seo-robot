# -*- coding: utf-8 -*-
from typing import Optional

# (اصلاح شده) ایمپورت‌ها
from .proxy_manager import proxy_manager
from .proxy_config_model import ProxyConfig
from core.logger import logger

def select_best_proxy() -> Optional[ProxyConfig]:
    logger.debug("در حال انتخاب بهترین پروکسی...")
    return proxy_manager.get_best_proxy()