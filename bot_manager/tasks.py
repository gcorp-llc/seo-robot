"""تسک‌های پس‌زمینه ربات SEO (اجرا توسط Django-Q)

بهبودها نسبت به نسخه قبل:
- رفع باگ‌ها: متد sync_proxies_task که تعریف نشده بود پیاده‌سازی شد،
  فیلتر کلمات کلیدی/موتورها اصلاح شد، اتصال مرورگر در همه مسیرهای خطا بسته می‌شود.
- جلوگیری از رشد بی‌حد لاگ Job (حفظ حداکثر ۵۰۰ خط آخر).
- ذخیره بهینه با update_fields و کاهش تعداد نوشتن در دیتابیس.
- ثبت لینک‌های کشف‌شده در مدل CrawledLink (استفاده از این مدل که قبلاً بلااستفاده بود).
- انتخاب هوشمند پروکسی: اولویت پروکسی‌هایی که اخیراً سالم بوده‌اند.
"""

import asyncio
import random
import traceback

import requests
from django.utils import timezone
from asgiref.sync import sync_to_async
from playwright.async_api import async_playwright

from bot_manager.models import BotJob, CrawledLink, Device, Keyword, Proxy, SearchEngine
from crawler.link_extractor import extract_internal_links
from crawler.search_engine import perform_search
from crawler.page_visit import visit_page_naturally, smart_click_and_visit
from urllib.parse import urlparse

MAX_LOG_LINES = 500
PROXY_TEST_URL = "https://www.google.com/generate_204"
PROXY_TEST_TIMEOUT = 10


# ---------- کمکی‌های Async -> ORM ----------

@sync_to_async
def get_job_with_site(job_id):
    return BotJob.objects.select_related('site').get(id=job_id)


@sync_to_async
def save_job_fields(job_id, **fields):
    """ذخیره فقط فیلدهای تغییرکرده (کمتر قفل کردن رکورد و کوئری سبک‌تر)."""
    BotJob.objects.filter(id=job_id).update(**fields)


@sync_to_async
def append_job_log(job_id, msg):
    """افزودن یک خط لاگ با سقف مشخص تا جدول BotJob بی‌حد بزرگ نشود."""
    job = BotJob.objects.get(id=job_id)
    timestamp = timezone.localtime().strftime("%H:%M:%S")
    lines = (job.log.splitlines() + [f"[{timestamp}] {msg}"])[-MAX_LOG_LINES:]
    job.log = "\n".join(lines) + "\n"
    job.save(update_fields=["log"])


@sync_to_async
def update_progress(job_id, progress, step):
    BotJob.objects.filter(id=job_id).update(progress=progress, current_step=step)


@sync_to_async
def get_active_proxies():
    # پروکسی‌های سالمِ recently-checked اولویت دارند
    return list(Proxy.objects.filter(is_active=True).order_by('-last_checked')[:200])


@sync_to_async
def get_active_devices():
    return list(Device.objects.filter(is_active=True))


@sync_to_async
def get_site_keywords(site_id):
    return list(Keyword.objects.filter(site_id=site_id))


@sync_to_async
def get_active_engines():
    return list(SearchEngine.objects.filter(is_active=True))


@sync_to_async
def record_crawled_links(site_id, urls):
    """ثبت لینک‌های کشف‌شده بدون ایجاد تکراری (bulk + ignore_conflicts)."""
    objs = [CrawledLink(site_id=site_id, url=u) for u in urls[:100]]
    if objs:
        CrawledLink.objects.bulk_create(objs, ignore_conflicts=True)


@sync_to_async
def mark_link_visited(site_id, url):
    CrawledLink.objects.update_or_create(
        site_id=site_id, url=url, defaults={"is_visited": True}
    )


async def run_seo_bot(job_id):
    job = await get_job_with_site(job_id)
    await save_job_fields(job_id, status='running')

    async def add_log(msg):
        await append_job_log(job_id, msg)

    browser = None
    try:
        await add_log(f"🚀 شروع عملیات هوشمند برای سایت: {job.site.name}")
        await update_progress(job_id, 5, "آماده‌سازی مرورگر و هویت دیجیتال")

        # انتخاب پروکسی و دستگاه
        active_proxies = await get_active_proxies()
        proxy_url = random.choice(active_proxies).url if active_proxies else None
        active_devices = await get_active_devices()
        device_config = random.choice(active_devices).config_json if active_devices else {}
        if not isinstance(device_config, dict):
            device_config = {}

        # حذف کلیدهای غیرمجاز context تا new_context خطا ندهد
        for key in ("name", "user_agent"):
            device_config.pop(key, None)

        async with async_playwright() as p:
            browser_args = ["--disable-blink-features=AutomationControlled"]

            proxy_settings = None
            if proxy_url:
                await add_log(f"🌐 استفاده از پروکسی: {proxy_url}")
                proxy_settings = {"server": proxy_url}

            browser = await p.chromium.launch(
                headless=True,
                args=browser_args,
                proxy=proxy_settings,
            )

            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent=device_config.pop(
                    'user_agent',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ),
                **device_config,
            )

            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = await context.new_page()
            domain = urlparse(job.site.main_url).netloc

            # مرحله ۱: جستجو و کلیک روی نتیجه هدف
            if job.site.search_engines_enabled:
                await update_progress(job_id, 20, "جستجوی کلمات کلیدی")

                keywords = await get_site_keywords(job.site.id)
                active_engines = await get_active_engines()

                if keywords and active_engines:
                    keyword_obj = random.choice(keywords)
                    engine_obj = random.choice(active_engines)
                    await add_log(f"🔍 در حال جستجوی '{keyword_obj.word}' در {engine_obj.name}...")

                    search_results = await perform_search(page, engine_obj.name, keyword_obj.word)

                    if search_results:
                        await add_log(f"✅ تعداد {len(search_results)} نتیجه استخراج شد. در حال تحلیل رتبه‌ها...")
                        found = await smart_click_and_visit(page, search_results, domain, page.url)
                        if found:
                            await add_log("🎯 سایت هدف با موفقیت پیدا و با رفتار انسانی بازدید شد.")
                            await mark_link_visited(job.site.id, page.url)
                            await update_progress(job_id, 60, "بازدید از طریق موتور جستجو")
                        else:
                            await add_log("⚠️ سایت در نتایج یافت نشد. استفاده از بازدید مستقیم...")
                    else:
                        await add_log("❌ نتایجی از موتور جستجو دریافت نشد.")
                else:
                    await add_log("⚠️ کلمه کلیدی یا موتور جستجوی فعال تعریف نشده است.")

            # مرحله ۲: بازدید مستقیم صفحه اصلی
            current = await sync_to_async(BotJob.objects.get)(job_id)
            if current.progress < 60:
                await update_progress(job_id, 65, "بازدید مستقیم و تعامل داخلی")
                await add_log(f"🏠 مراجعه مستقیم به: {job.site.main_url}")
                await visit_page_naturally(page, job.site.main_url, domain)
                await update_progress(job_id, 70, "تعامل با صفحه اصلی")

            # مرحله ۳: کرال بخش مقالات و مطالعه عمیق
            await update_progress(job_id, 75, "تعامل عمیق با محتوا")

            await page.goto(job.site.articles_url, wait_until="domcontentloaded", timeout=45000)
            links = await extract_internal_links(page, job.site.articles_url, domain)
            await record_crawled_links(job.site.id, links)

            if links:
                max_visits = min(len(links), max(1, job.site.visits_per_run))
                visit_count = random.randint(1, max_visits)
                selected_links = random.sample(links, visit_count)
                await add_log(f"📝 انتخاب هوشمند {visit_count} مقاله از {len(links)} لینک کشف‌شده...")

                for i, link in enumerate(selected_links):
                    await add_log(f"📖 مطالعه مقاله {i + 1}: {link}")
                    await visit_page_naturally(page, link, domain)
                    await mark_link_visited(job.site.id, link)
                    await asyncio.sleep(random.uniform(5, 15))
            else:
                await add_log("ℹ️ لینک داخلی جدیدی برای مطالعه یافت نشد.")

            await update_progress(job_id, 95, "پایان عملیات")
            await asyncio.sleep(random.uniform(5, 10))

        await save_job_fields(
            job_id,
            status='completed', progress=100,
            finished_at=timezone.now(), current_step="تکمیل شده",
        )
        await add_log("✅ عملیات با موفقیت و رفتار انسانی کامل به پایان رسید.")

    except Exception as e:
        error_msg = f"❌ خطا: {str(e)}"
        await add_log(error_msg)
        await add_log(traceback.format_exc().splitlines()[-3] if traceback.format_exc() else "")
        await save_job_fields(
            job_id,
            status='failed', finished_at=timezone.now(), current_step="ناموفق",
        )
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass


def run_bot_task(site_id, job_id):
    """نقطه ورود Django-Q (sync wrapper)."""
    asyncio.run(run_seo_bot(job_id))


# ---------- همگام‌سازی و بررسی پروکسی‌ها ----------

def _normalize_proxy_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "://" in line:
        return line
    # فرمت ip:port یا ip:port:user:pass
    parts = line.split(":")
    if len(parts) >= 2:
        return f"http://{line}"
    return None


def _test_proxy(proxy_url, test_url=PROXY_TEST_URL, timeout=PROXY_TEST_TIMEOUT):
    """سلامت یک پروکسی را تست می‌کند؛ خروجی: (ok, status_code, latency_ms)."""
    start = timezone.now()
    try:
        resp = requests.get(
            test_url, proxies={"http": proxy_url, "https": proxy_url}, timeout=timeout
        )
        latency = int((timezone.now() - start).total_seconds() * 1000)
        return resp.status_code in (200, 204, 301, 302), resp.status_code, latency
    except requests.RequestException:
        latency = int((timezone.now() - start).total_seconds() * 1000)
        return False, None, latency


def sync_proxies_task(source_id):
    """دریافت لیست پروکسی از یک منبع URL و ذخیره آن‌ها در دیتابیس."""
    from bot_manager.models import ProxySource

    try:
        source = ProxySource.objects.get(id=source_id)
    except ProxySource.DoesNotExist:
        return "منبع پروکسی یافت نشد"

    try:
        resp = requests.get(source.url, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        return f"خطا در دریافت لیست پروکسی: {e}"

    added = 0
    for raw_line in resp.text.splitlines():
        proxy_url = _normalize_proxy_line(raw_line)
        if not proxy_url:
            continue
        _, created = Proxy.objects.get_or_create(
            url=proxy_url[:255], defaults={"is_active": True}
        )
        if created:
            added += 1

    source.save()  # بروزرسانی last_sync
    return f"{added} پروکسی جدید به دیتابیس افزوده شد."


def check_proxies_task(limit=100):
    """بررسی سلامت پروکسی‌های فعال و non-active کردن پروکسی‌های خراب."""
    proxies = list(Proxy.objects.filter(is_active=True)[:limit])
    healthy = 0
    for proxy in proxies:
        ok, code, latency = _test_proxy(proxy.url)
        proxy.is_active = ok
        proxy.status_code = code
        proxy.latency_ms = latency
        proxy.last_checked = timezone.now()
        proxy.save(update_fields=["is_active", "status_code", "latency_ms", "last_checked"])
        if ok:
            healthy += 1
    return f"بررسی {len(proxies)} پروکسی انجام شد؛ {healthy} پروکسی سالم است."
