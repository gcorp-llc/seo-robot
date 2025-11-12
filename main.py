# -*- coding: utf-8 -*-
import asyncio
import random
import sys
import inspect
from typing import List, Optional, Dict, Any

# افزودن ایمپورت‌های مورد نیاز برای fallback خواندن CSV / API
import csv
import os
from typing import Set
import re  # << اضافه شد برای جستجوی الگوهای پروکسی در متن
try:
    import requests
except Exception:
    requests = None

# ایمپورت توابع کمکی برای پارس CSV (فایل جدید)
try:
    from proxy_utils import create_proxy_from_csv_row
except Exception:
    create_proxy_from_csv_row = None

# --- ایمپورت‌های به‌روز شده ---
from config import TARGETS, USE_PROXY_ROTATION
# 'proxy_manager' از 'config' حذف شد، چون از فایل جدید ایمپورت می‌شود
# 'get_active_proxies_advanced' حذف شد

# ایمپورت کردن نمونه (instance) مدیر پروکسی جدید
from network.proxy_manager import proxy_manager
# ایمپورت کردن توابع کمکی جدید
from network.proxy_checker import run_proxy_validation

from core import logger, performance_monitor
from core.error_handler import global_error_handler
from browser.pool import get_browser_from_pool, cleanup_browser_pool
from playwright.async_api import async_playwright
from devices.processor import process_device
from config.general_settings import DEVICES
from config.proxy_config import PROXY_CSV_FILE, PROXY_API_URL, MANUAL_PROXIES

# --- (اختیاری) تنظیمات بارگذاری پروکسی ---
# مکان فایل CSV پروکسی خود را مشخص کنید
# PROXY_CSV_FILE = 'proxies-export.csv' 

# (اختیاری) آدرس یک API که لیست پروکسی می‌دهد
# PROXY_API_URL = 'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http'

# (اختیاری) لیست پروکسی‌های دستی
# MANUAL_PROXIES = ['http://1.2.3.4:8080']


async def main():
    logger.info("="*80)
    logger.info("🚀 ربات SEO - شروع برنامه (نسخه بازدید هوشمند)")
    logger.info("="*80)
    logger.info(f"🎯 تعداد اهداف: {len(TARGETS)}")
    logger.info(f"📱 تعداد دستگاه‌ها: {len(DEVICES)}")
    logger.info("="*80)
    
    # --- مرحله ۱: بارگذاری و اعتبارسنجی پروکسی (بخش جدید) ---
    logger.info("... در حال بارگذاری و اعتبارسنجی پروکسی‌ها ...")
    try:
        # فراخوانی امن: ممکن است load_proxies_from_csv sync یا async باشد
        loader = getattr(proxy_manager, 'load_proxies_from_csv', None)
        if loader:
            try:
                if inspect.iscoroutinefunction(loader):
                    try:
                        await loader(PROXY_CSV_FILE)
                    except TypeError:
                        # بعضی پیاده‌سازی‌ها پارامتر path ندارند
                        await loader()
                else:
                    try:
                        loader(PROXY_CSV_FILE)
                    except TypeError:
                        loader()
            except Exception as e:
                logger.debug(f"خطا در اجرای loader پروکسی: {e}", exc_info=True)
        else:
            logger.debug("proxy_manager.load_proxies_from_csv در دسترس نیست؛ به fallback ادامه می‌دهیم.")

        # اگر هیچ پروکسی اضافه نشده بود، fallback محلی اجرا کنید
        if not proxy_manager.proxies:
            logger.info(f"پوشش جانبی: تلاش برای خواندن مستقیم CSV ({PROXY_CSV_FILE}) با fallback محلی...")
            added_set: Set[str] = set()
            if os.path.exists(PROXY_CSV_FILE):
                try:
                    # باز کردن با utf-8-sig تا BOM نیز حذف شود
                    with open(PROXY_CSV_FILE, newline='', encoding='utf-8-sig') as f:
                        # سعی می‌کنیم هم DictReader و هم ساده را پشتیبانی کنیم
                        reader = csv.DictReader(f)
                        # اگر فایل header نداشت، DictReader.fieldnames ممکن است None یا [None]
                        if not reader.fieldnames or all(fn is None for fn in reader.fieldnames):
                            f.seek(0)
                            # fallback به reader ساده
                            simple = csv.reader(f)
                            for row in simple:
                                if not row:
                                    continue
                                proxy_str = None
                                if create_proxy_from_csv_row:
                                    proxy_str = create_proxy_from_csv_row(row)
                                else:
                                    proxy_str = str(row[0]).strip()
                                # اگر یک سلول شامل چند پروکسی با کاما/سیمی‌کالن باشد، جدا کن
                                if proxy_str and (',' in proxy_str or ';' in proxy_str):
                                    parts = re.split(r'[;,]\s*', proxy_str)
                                    for p in parts:
                                        if p:
                                            added_set.add(p.strip())
                                elif proxy_str:
                                    added_set.add(proxy_str)
                        else:
                            f.seek(0)
                            reader = csv.DictReader(f)
                            for row in reader:
                                proxy_str = None
                                if create_proxy_from_csv_row:
                                    proxy_str = create_proxy_from_csv_row(row)
                                else:
                                    # تلاش برای خواندن یکی از ستون‌های معمول
                                    for key in ('proxy', 'address', 'ip', 'host'):
                                        if key in row and row[key]:
                                            proxy_str = str(row[key]).strip()
                                            break
                                if proxy_str:
                                    # جداکننده‌های درون سلولی
                                    if ',' in proxy_str or ';' in proxy_str:
                                        parts = re.split(r'[;,]\s*', proxy_str)
                                        for p in parts:
                                            if p:
                                                added_set.add(p.strip())
                                    else:
                                        added_set.add(proxy_str)
                except Exception as e:
                    logger.debug(f"fallback خواندن CSV با خطا مواجه شد: {e}", exc_info=True)

                # اگر هنوز پروکسی‌ای پیدا نشده بود، فایل را متن-محور جستجو کن (regex)
                if not added_set:
                    try:
                        with open(PROXY_CSV_FILE, 'r', encoding='utf-8-sig', errors='ignore') as f:
                            content = f.read()
                            # الگو برای host:port با یا بدون scheme، همچنین پشتیبانی از دامنه به‌علاوه IP
                            pattern = re.compile(
                                r'(?:(?:http|https|socks5|socks4)://)?'  # optional scheme
                                r'(?:[A-Za-z0-9\-\._~%]+\.)*[A-Za-z0-9\-\._~%]+'  # hostname or IP-like token
                                r'(?:\:\d{1,5})'  # :port
                            )
                            matches = pattern.findall(content)
                            for m in matches:
                                m = m.strip().strip('"').strip("'")
                                if m:
                                    added_set.add(m)
                    except Exception as e:
                        logger.debug(f"regex fallback خواندن فایل با خطا مواجه شد: {e}", exc_info=True)

            if added_set:
                proxies_list = list(added_set)

                # --- robust اضافه کردن پروکسی‌ها به proxy_manager ---
                def _robust_add_proxies(proxies_list):
                    import inspect as _inspect
                    added = 0
                    logger.info(f"در حال اضافه کردن {len(proxies_list)} پروکسی به صورت دستی...")
                    # تشخیص و لاگ وضعیت فعلی proxy_manager
                    try:
                        pm_proxies = getattr(proxy_manager, 'proxies', None)
                        pm_active = getattr(proxy_manager, 'active_proxies', None)
                        logger.debug(f"proxy_manager has add_manual_proxies={hasattr(proxy_manager, 'add_manual_proxies')}, "
                                     f"add_proxies={hasattr(proxy_manager, 'add_proxies')}, add_proxy={hasattr(proxy_manager, 'add_proxy')}")
                        logger.debug(f"proxy_manager.proxies type={type(pm_proxies)}, len(before)={len(pm_proxies) if isinstance(pm_proxies, (list,tuple)) else 'n/a'}")
                    except Exception:
                        logger.debug("خطا در خواندن وضعیت اولیه proxy_manager", exc_info=True)

                    # helper جدید: تلاش برای برگشت لیست واقعی پروکسی‌ها به صورت امن
                    def _get_proxies_list():
                        try:
                            attr = getattr(proxy_manager, 'proxies', None)
                            # اگر خودِ attribute یک callable است، سعی کن آن را اجرا کنی
                            if callable(attr):
                                try:
                                    val = attr()
                                    if isinstance(val, (list, tuple)):
                                        return list(val)
                                    try:
                                        return list(val)
                                    except Exception:
                                        return None
                                except Exception:
                                    # اگر اجرای callable ناموفق بود، ادامه می‌دهیم
                                    pass
                            # اگر attribute لیست است
                            if isinstance(attr, (list, tuple)):
                                return list(attr)
                            # اگر proxy_manager متد کمکی برای گرفتن همه URLها دارد، از آن استفاده کن
                            if hasattr(proxy_manager, 'get_all_proxy_urls'):
                                try:
                                    val = proxy_manager.get_all_proxy_urls()
                                    if isinstance(val, (list, tuple)):
                                        return list(val)
                                except Exception:
                                    pass
                            # اگر property یا iterable دیگری است، تلاش تبدیل به لیست
                            if attr is not None:
                                try:
                                    return list(attr)
                                except Exception:
                                    return None
                            return None
                        except Exception:
                            return None

                    def _count_before():
                        lst = _get_proxies_list()
                        return len(lst) if isinstance(lst, (list, tuple)) else None

                    before = _count_before()

                    # 1) تلاش با متد add_manual_proxies اگر وجود دارد
                    if hasattr(proxy_manager, 'add_manual_proxies'):
                        try:
                            logger.debug("تلاش برای افزودن با add_manual_proxies()")
                            res = proxy_manager.add_manual_proxies(proxies_list)
                            if isinstance(res, int):
                                added = res
                            elif isinstance(res, list):
                                added = len(res)
                            else:
                                after = _count_before()
                                if before is not None and after is not None:
                                    added = max(0, after - (before or 0))
                        except Exception as e:
                            logger.debug(f"add_manual_proxies ناموفق بود: {e}", exc_info=True)

                    # 2) تلاش با add_proxies در صورت وجود
                    if added == 0 and hasattr(proxy_manager, 'add_proxies'):
                        try:
                            logger.debug("تلاش برای افزودن با add_proxies()")
                            res = proxy_manager.add_proxies(proxies_list)
                            if isinstance(res, int):
                                added = res
                            elif isinstance(res, list):
                                added = len(res)
                            else:
                                after = _count_before()
                                if before is not None and after is not None:
                                    added = max(0, after - (before or 0))
                        except Exception as e:
                            logger.debug(f"add_proxies ناموفق بود: {e}", exc_info=True)

                    # 3) تلاش برای ساخت ProxyConfig از network.proxy_manager (در اولویت) یا config.proxy_config
                    if added == 0 and hasattr(proxy_manager, 'add_proxy'):
                        try:
                            # تلاش برای استفاده از کلاس ProxyConfig بسته network اگر موجود است
                            NetProxyConfig = None
                            try:
                                from network.proxy_manager import ProxyConfig as NetProxyConfig  # type: ignore
                                logger.debug("استفاده از ProxyConfig از network.proxy_manager")
                            except Exception:
                                NetProxyConfig = None
                            # fallback به config.proxy_config.ProxyConfig
                            from config.proxy_config import ProxyConfig as ConfProxyConfig, ProxyType as ConfProxyType

                            converted = []
                            for p in proxies_list:
                                s = str(p).strip()
                                if not s:
                                    continue
                                scheme = None
                                hostport = s
                                if '://' in s:
                                    scheme, hostport = s.split('://', 1)
                                if ':' in hostport:
                                    host, port = hostport.rsplit(':', 1)
                                else:
                                    host, port = hostport, '0'
                                # انتخاب proto امن
                                try:
                                    proto = ConfProxyType(scheme.lower()) if scheme else ConfProxyType.HTTP
                                except Exception:
                                    try:
                                        proto = ConfProxyType[scheme.upper()] if scheme else ConfProxyType.HTTP
                                    except Exception:
                                        proto = ConfProxyType.HTTP
                                try:
                                    if NetProxyConfig:
                                        pc = NetProxyConfig(url=s, ip=host, port=int(port or 0), protocol=proto)  # type: ignore
                                    else:
                                        pc = ConfProxyConfig(url=s, ip=host, port=int(port or 0), protocol=proto)
                                    converted.append(pc)
                                except Exception:
                                    logger.debug(f"خطا در ساخت ProxyConfig برای {s}", exc_info=True)
                                    continue
                            # افزودن با متد add_proxy یا الحاق مستقیم
                            if converted:
                                for pc in converted:
                                    try:
                                        proxy_manager.add_proxy(pc)
                                    except Exception:
                                        try:
                                            if hasattr(proxy_manager, 'proxies') and isinstance(getattr(proxy_manager, 'proxies'), list):
                                                getattr(proxy_manager, 'proxies').append(pc)
                                        except Exception:
                                            logger.debug("عدم توانایی در افزودن ProxyConfig", exc_info=True)
                                after = _count_before()
                                if before is not None and after is not None:
                                    added = max(0, after - (before or 0))
                        except Exception as e:
                            logger.debug(f"تلاش برای تبدیل به ProxyConfig ناموفق بود: {e}", exc_info=True)

                    # 4) الحاق رشته‌ای مستقیم اگر هنوز اضافه نشده
                    if added == 0:
                        try:
                            # دریافت لیست فعلی (ایمن)
                            current = _get_proxies_list()
                            if isinstance(current, list):
                                existing_set = set(str(x) for x in current)
                                to_add = [p for p in proxies_list if str(p) not in existing_set]
                                # اگر proxy_manager.proxies خودِ یک لیست قابل نوشتن است، الحاق کن
                                attr = getattr(proxy_manager, 'proxies', None)
                                if isinstance(attr, list):
                                    attr.extend(to_add)
                                else:
                                    # تلاش برای استفاده از add_proxy برای هر رشته
                                    if hasattr(proxy_manager, 'add_proxy'):
                                        for s in to_add:
                                            try:
                                                # ساخت ProxyConfig از config برای رشته‌ها
                                                from config.proxy_config import ProxyConfig as ConfProxyConfig, ProxyType as ConfProxyType
                                                sch = None
                                                hp = str(s)
                                                if '://' in hp:
                                                    sch, hp = hp.split('://', 1)
                                                if ':' in hp:
                                                    h, pr = hp.rsplit(':',1)
                                                else:
                                                    h, pr = hp, 0
                                                proto = ConfProxyType.HTTP
                                                try:
                                                    proto = ConfProxyType(sch.lower()) if sch else ConfProxyType.HTTP
                                                except Exception:
                                                    pass
                                                pc = ConfProxyConfig(url=str(s), ip=h, port=int(pr or 0), protocol=proto)
                                                proxy_manager.add_proxy(pc)
                                            except Exception:
                                                logger.debug("عدم توانایی در افزودن رشته به عنوان ProxyConfig", exc_info=True)
                                    else:
                                        logger.debug("نمی‌توان به طور مستقیم پروکسی‌ها را الحاق کرد؛ proxy_manager.proxies لیست قابل نوشتن نیست و متد افزودن وجود ندارد.")
                                after = _count_before()
                                if before is not None and after is not None:
                                    added = max(0, after - (before or 0))
                        except Exception as e:
                            logger.debug(f"الحاق رشته‌ای پروکسی‌ها ناموفق بود: {e}", exc_info=True)

                    # 5) همگام‌سازی active_proxies در صورت وجود
                    try:
                        if hasattr(proxy_manager, 'active_proxies') and isinstance(getattr(proxy_manager, 'active_proxies'), list):
                            new_active = []
                            cur = _get_proxies_list()
                            if isinstance(cur, list):
                                for item in cur:
                                    if hasattr(item, 'is_active'):
                                        if getattr(item, 'is_active', True):
                                            new_active.append(item)
                                    else:
                                        new_active.append(item)
                                proxy_manager.active_proxies = new_active
                    except Exception:
                        logger.debug("همگام‌سازی active_proxies ناموفق بود", exc_info=True)

                    # لاگ نمونه و تعداد نهایی
                    try:
                        final_len = _count_before()
                        logger.info(f"تعداد اضافه شده: {added}; طول نهایی proxy_manager.proxies = {final_len}")
                        sample = _get_proxies_list() or []
                        logger.debug(f"نمونه پروکسی‌ها بعد از افزودن: {sample[:5]}")
                    except Exception:
                        logger.debug("خطا در لاگ‌نهایی", exc_info=True)

                    logger.info(f"{added} پروکسی جدید از CSV به صورت دستی اضافه شد." if added else "0 پروکسی جدید به صورت دستی اضافه شد.")
                    # اگر نتایج صفر باقی بماند، لاگ صریح برای بررسی network/proxy_manager.py
                    if added == 0:
                        logger.warning("تلاش‌ها برای افزودن پروکسی‌ها نتیجه‌ای نداده است؛ لطفاً فایل network/proxy_manager.py را ارسال کنید تا نوع داده و API مورد انتظار بررسی شود.")
                    return added

                # اجرای تابع robust اضافه کردن
                _robust_add_proxies(proxies_list)
            else:
                logger.info("0 پروکسی جدید از CSV اضافه شد.")
        
        # (گزینه ب - اختیاری) بارگذاری از API (اگر متغیر PROXY_API_URL را تنظیم کنید)
        # مثال ساده: پاسخ متن خط‌به‌خط شامل host:port باشد
        if 'PROXY_API_URL' in globals() and globals().get('PROXY_API_URL'):
            api_url = globals().get('PROXY_API_URL')
            logger.info(f"بارگذاری پروکسی‌ها از API: {api_url}")
            try:
                if requests is None:
                    logger.warning("کتابخانه requests در دسترس نیست؛ بارگذاری از API نادیده گرفته شد.")
                else:
                    resp = requests.get(api_url, timeout=10)
                    if resp.status_code == 200:
                        lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]
                        if lines:
                            if hasattr(proxy_manager, 'add_manual_proxies'):
                                proxy_manager.add_manual_proxies(lines)
                            else:
                                proxy_manager.proxies.extend([p for p in lines if p not in proxy_manager.proxies])
                            logger.info(f"{len(lines)} پروکسی از API اضافه شد.")
                    else:
                        logger.warning(f"دریافت لیست پروکسی از API موفق نبود: {resp.status_code}")
            except Exception as e:
                logger.debug(f"خطا در بارگذاری پروکسی از API: {e}", exc_info=True)

        # (گزینه ج - اختیاری) بارگذاری دستی
        # if MANUAL_PROXIES:
        #     proxy_manager.add_manual_proxies(MANUAL_PROXIES)

        # بررسی اینکه آیا اصلاً پروکسی بارگذاری شده است
        if not proxy_manager.proxies:
            logger.error("❌ هیچ پروکسی (از هیچ منبعی) بارگذاری نشد.")
            return

        # (مهم) اجرای اعتبارسنجی
        await run_proxy_validation()
        
        # دریافت لیست نهایی پروکسی‌های فعال
        active_proxies = proxy_manager.get_active_proxies()
        
    except Exception as e:
        logger.error(f"❌ خطا در بارگذاری یا بررسی پروکسی‌ها: {e}", exc_info=True)
        active_proxies = []
    # --- پایان بخش جدید ---
    
    if not active_proxies:
        logger.error("❌ هیچ پروکسی فعالی پس از بررسی یافت نشد!")
        # شما می‌توانید در اینجا گزینه 'None' (بدون پروکسی) را اضافه کنید اگر می‌خواهید
        # active_proxies = [None]
        # logger.warning("⚠️ ادامه کار بدون پروکسی...")
        return # یا خروج کامل
    
    # این بخش برای اطمینان از لیست بودن است، اگرچه get_active_proxies همیشه لیست برمی‌گرداند
    if not isinstance(active_proxies, list):
        try:
            active_proxies = list(active_proxies)
        except Exception:
            active_proxies = [active_proxies]
    
    logger.info(f"🔌 تعداد پروکسی‌های فعال و معتبر: {len(active_proxies)}")
    
    async with async_playwright() as playwright:
        # محدودیت همزمانی برای تسک‌های اصلی (پردازش اهداف)
        # شما این را 3 گذاشته بودید، من آن را حفظ می‌کنم
        semaphore = asyncio.Semaphore(3)
        
        async def process_target(target: Dict[str, Any]):
            async with semaphore:
                # انتخاب پروکسی‌ها برای چرخش
                proxy_rotation_list = active_proxies if USE_PROXY_ROTATION else [random.choice(active_proxies)]
                
                for proxy in proxy_rotation_list:
                    # پشتیبانی از 'None' اگر آن را دستی اضافه کرده باشید
                    proxy_str = getattr(proxy, "url", None) or "بدون پروکسی"
                    logger.info(f"\n🔌 پروکسی: {proxy_str} (برای {target['TARGET_DOMAIN']})")
                    
                    try:
                        browser = await get_browser_from_pool(playwright, proxy)
                        
                        num_devices = random.randint(1, min(3, len(DEVICES)))
                        selected_devices = random.sample(DEVICES, num_devices)
                        
                        for device in selected_devices:
                            await process_device(playwright, browser, device, proxy, target)
                            delay = random.uniform(10, 20)
                            await asyncio.sleep(delay)
                        
                        # تاخیر کوتاه بین پروکسی‌ها در چرخش
                        if proxy_rotation_list.index(proxy) < len(proxy_rotation_list) - 1:
                            delay = random.uniform(15, 30)
                            await asyncio.sleep(delay)
                            
                    except Exception as e:
                        logger.error(f"❌ خطا در استفاده از پروکسی {proxy_str}: {e}", exc_info=True)
                        
                        # --- (مهم) اصلاح نحوه علامت‌گذاری خطا ---
                        # اگر پروکسی آبجکت معتبر 'ProxyConfig' باشد
                        if proxy and hasattr(proxy, 'mark_failed'):
                            try:
                                # به جای proxy_manager.mark_failed()...
                                proxy.mark_failed()
                                logger.warning(f"⚠️ پروکسی {proxy_str} به عنوان ناموفق علامت‌گذاری شد.")
                            except Exception as mark_e:
                                logger.debug(f"⚠️ خطا در علامت‌گذاری پروکسی: {mark_e}", exc_info=True)
                        continue
        
        tasks = [process_target(target) for target in TARGETS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # لاگ کردن هر خطایی که از gather برمی‌گردد
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"❌ خطا در اجرای تسک اصلی: {r}", exc_info=True)
        
        await cleanup_browser_pool()
    
    logger.info("\n" + "="*80)
    logger.info("✅ برنامه با موفقیت به پایان رسید")
    logger.info("="*80)
    
    summary = performance_monitor.get_summary()
    logger.info("\n📊 آمار نهایی عملکرد:")
    logger.info(f"   ⏱️  زمان اجرا: {summary['runtime_minutes']:.1f} دقیقه")
    logger.info(f"   🔍 نرخ موفقیت جستجو: {summary['search_success_rate']:.1f}%")
    logger.info(f"   🌐 نرخ موفقیت بازدید: {summary['visit_success_rate']:.1f}%")
    logger.info(f"   📊 میانگین زمان جستجو: {summary['avg_search_time']:.1f} ثانیه")
    logger.info(f"   ⏰ میانگین زمان بازدید: {summary['avg_visit_time']:.1f} ثانیه")
    logger.info(f"   ❌ تعداد خطاها: {summary['total_errors']}")
    logger.info(f"   🔌 نرخ شکست پروکسی: {summary['proxy_failure_rate']:.1f}%")
    logger.info(f"   🤖 نرخ مواجهه با CAPTCHA: {summary['captcha_rate']:.1f}%")
    
    performance_monitor.save_report()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("\n⚠️ برنامه توسط کاربر متوقف شد")
    except Exception as e:
        logger.critical(f"❌ خطای بحرانی: {e}", exc_info=True)
        sys.exit(1)