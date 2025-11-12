# -*- coding: utf-8 -*-
import asyncio
from typing import List, Optional

# اصلاح ایمپورت‌ها: از ایمپورت نسبی برای استفاده داخل پکیج 'network' استفاده می‌کنیم
from .proxy_manager import proxy_manager, ProxyConfig

# هماهنگ با main.py: logger را از core وارد می‌کنیم (همان شیء logger که در main استفاده می‌شود)
from core import logger

# تنظیمات را می‌توان از فایل کانفیگ اصلی خواند
CONCURRENCY = 50 

async def run_proxy_validation():
    """
    (ساده‌سازی شده) - این تابع اکنون فقط به عنوان یک wrapper
    برای اجرای بررسی در proxy_manager عمل می‌کند.
    """
    logger.info("در حال شروع فرآیند بررسی پروکسی‌ها...")
    try:
        await proxy_manager.run_proxy_validation(concurrency=CONCURRENCY)
        logger.info("فرآیند بررسی پروکسی‌ها با موفقیت تمام شد.")
    except Exception as e:
        logger.error(f"خطا در هنگام اجرای بررسی پروکسی‌ها: {e}")

async def get_active_proxies() -> List[ProxyConfig]:
    """
    (ساده‌سازی شده) - پروکسی‌های فعال را مستقیماً از مدیر پروکسی دریافت می‌کند.
    """
    active_list = proxy_manager.get_active_proxies()
    logger.info(f"تعداد {len(active_list)} پروکسی فعال بازگردانده شد.")
    return active_list