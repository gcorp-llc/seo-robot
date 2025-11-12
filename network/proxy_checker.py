# -*- coding: utf-8 -*-
import asyncio
from typing import List, Optional, Dict

# اصلاح ایمپورت‌ها
from .proxy_manager import proxy_manager
from .proxy_config_model import ProxyConfig

from core import logger

CONCURRENCY = 50 
TEST_URL = "http://httpbin.org/ip"

async def run_proxy_validation(verbose: bool = True):
    """
    بررسی و گزارش‌دهی پروکسی‌ها با فرمت جامع
    """
    logger.info("در حال شروع فرآیند بررسی پروکسی‌ها...")
    
    try:
        results = await proxy_manager.run_proxy_validation(
            concurrency=CONCURRENCY,
            test_url=TEST_URL
        )
        
        if verbose:
            _print_validation_report(results)
        
        logger.info("فرآیند بررسی پروکسی‌ها با موفقیت تمام شد.")
        
    except Exception as e:
        logger.error(f"خطا در هنگام اجرای بررسی پروکسی‌ها: {e}", exc_info=True)

def _print_validation_report(results: Dict):
    """چاپ گزارش جامع بررسی پروکسی‌ها"""
    
    if not results:
        logger.warning("هیچ نتیجه‌ای از بررسی پروکسی دریافت نشد")
        return
    
    working = results.get('working', [])
    failed = results.get('failed', [])
    timeout = results.get('timeout', [])
    errors = results.get('errors', [])
    
    total = len(working) + len(failed) + len(timeout) + len(errors)
    
    # سرتیتر
    print("\n" + "="*80)
    print("📊 گزارش بررسی پروکسی‌ها")
    print("="*80)
    
    # نتایج موفق
    if working:
        print(f"\n✅ پروکسی‌های فعال ({len(working)}):")
        print("-"*80)
        for proxy_info in working:
            proxy_url = proxy_info.get('proxy', 'Unknown')
            response_time = proxy_info.get('time', 0)
            ip = proxy_info.get('ip', 'Unknown')
            print(f"  ✅ {proxy_url:40} - {response_time:8.2f}ms - IP: {ip}")
    
    # نتایج ناموفق (Status Error)
    if failed:
        print(f"\n⚠️  پروکسی‌های ناموفق ({len(failed)}):")
        print("-"*80)
        for proxy_info in failed:
            proxy_url = proxy_info.get('proxy', 'Unknown')
            status = proxy_info.get('error', 'Unknown')
            print(f"  ⚠️  {proxy_url:40} - {status}")
    
    # نتایج timeout
    if timeout:
        print(f"\n⏰ پروکسی‌های timeout ({len(timeout)}):")
        print("-"*80)
        for proxy_url in timeout:
            print(f"  ⏰ {proxy_url:40} - Timeout")
    
    # نتایج خطا
    if errors:
        print(f"\n❌ پروکسی‌های با خطا ({len(errors)}):")
        print("-"*80)
        for proxy_info in errors:
            proxy_url = proxy_info.get('proxy', 'Unknown')
            error = proxy_info.get('error', 'Unknown')
            print(f"  ❌ {proxy_url:40} - {error[:50]}")
    
    # خلاصه
    print("\n" + "="*80)
    print(f"📈 خلاصه: {len(working)} از {total} پروکسی کار می‌کند")
    print("="*80)
    
    if working:
        print("\n✅ پروکسی‌های قابل استفاده:")
        for proxy_info in working:
            print(f"  • {proxy_info.get('proxy', 'Unknown')}")
    
    print()

async def get_active_proxies() -> List[ProxyConfig]:
    """دریافت پروکسی‌های فعال"""
    active_list = proxy_manager.get_active_proxies()
    logger.info(f"تعداد {len(active_list)} پروکسی فعال بازگردانده شد.")
    return active_list