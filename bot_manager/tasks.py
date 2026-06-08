import asyncio
import random
from django.utils import timezone
from asgiref.sync import sync_to_async
from playwright.async_api import async_playwright
from bot_manager.models import BotJob, SiteConfig, Keyword, SearchEngine, Proxy, Device, CrawledLink
from crawler.link_extractor import extract_internal_links
from crawler.search_engine import perform_search
from crawler.page_visit import visit_page_naturally, smart_click_and_visit
from urllib.parse import urlparse

@sync_to_async
def get_job_with_site(job_id):
    return BotJob.objects.select_related('site').get(id=job_id)

@sync_to_async
def save_job(job):
    job.save()

@sync_to_async
def get_active_proxies():
    return list(Proxy.objects.filter(is_active=True))

@sync_to_async
def get_active_devices():
    return list(Device.objects.filter(is_active=True))

@sync_to_async
def get_site_keywords(site_id):
    return list(Keyword.objects.filter(site_id=site_id))

@sync_to_async
def get_active_engines():
    return list(SearchEngine.objects.filter(is_active=True))

async def run_seo_bot(job_id):
    job = await get_job_with_site(job_id)
    job.status = 'running'
    await save_job(job)

    async def add_log(msg):
        timestamp = timezone.now().strftime("%H:%M:%S")
        job.log += f"[{timestamp}] {msg}\n"
        await save_job(job)

    try:
        await add_log(f"🚀 شروع عملیات هوشمند برای سایت: {job.site.name}")
        job.progress = 5
        job.current_step = "آماده‌سازی مرورگر و هویت دیجیتال"
        await save_job(job)

        # انتخاب پروکسی و دستگاه
        active_proxies = await get_active_proxies()
        proxy_url = random.choice(active_proxies).url if active_proxies else None
        active_devices = await get_active_devices()
        device_config = random.choice(active_devices).config_json if active_devices else {}

        async with async_playwright() as p:
            browser_args = ["--disable-blink-features=AutomationControlled"]

            # اعمال تنظیمات پروکسی
            proxy_settings = None
            if proxy_url:
                await add_log(f"🌐 استفاده از پروکسی: {proxy_url}")
                proxy_settings = {"server": proxy_url}

            browser = await p.chromium.launch(
                headless=True,
                args=browser_args,
                proxy=proxy_settings
            )

            context = await browser.new_context(
                **device_config,
                viewport={'width': 1280, 'height': 720},
                user_agent=device_config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            )

            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            page = await context.new_page()
            domain = urlparse(job.site.main_url).netloc

            # مرحله 1: جستجو و کلیک (SEO اصلی)
            if job.site.search_engines_enabled:
                job.progress = 20
                job.current_step = "جستجوی کلمات کلیدی"
                await save_job(job)

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
                            job.progress = 60
                        else:
                            await add_log("⚠️ سایت در نتایج یافت نشد. استفاده از بازدید مستقیم...")
                    else:
                        await add_log("❌ نتایجی از موتور جستجو دریافت نشد.")
                else:
                    await add_log("⚠️ کلمه کلیدی یا موتور جستجوی فعال تعریف نشده است.")

            # مرحله 2: کرال و تعامل داخلی
            if job.progress < 60:
                job.current_step = "بازدید مستقیم و تعامل داخلی"
                await save_job(job)
                await add_log(f"🏠 مراجعه مستقیم به: {job.site.main_url}")
                await visit_page_naturally(page, job.site.main_url, domain)
                job.progress = 70

            # مرحله 3: تعامل با مقالات
            job.current_step = "تعامل عمیق با محتوا"
            await save_job(job)

            await page.goto(job.site.articles_url, wait_until="networkidle")
            links = await extract_internal_links(page, job.site.articles_url, domain)

            if links:
                visit_count = random.randint(1, min(len(links), 3))
                selected_links = random.sample(links, visit_count)
                await add_log(f"📝 انتخاب هوشمند {visit_count} مقاله برای مطالعه...")

                for i, link in enumerate(selected_links):
                    await add_log(f"📖 مطالعه مقاله {i+1}: {link}")
                    await visit_page_naturally(page, link, domain)
                    await asyncio.sleep(random.uniform(5, 15))

            job.progress = 95
            job.current_step = "پایان عملیات"
            await save_job(job)

            await asyncio.sleep(random.uniform(5, 10))
            await browser.close()

        job.status = 'completed'
        job.progress = 100
        job.finished_at = timezone.now()
        job.current_step = "تکمیل شده"
        await add_log("✅ عملیات با موفقیت و رفتار انسانی کامل به پایان رسید.")
        await save_job(job)

    except Exception as e:
        import traceback
        error_msg = f"❌ خطا: {str(e)}\n{traceback.format_exc()}"
        await add_log(error_msg)
        job.status = 'failed'
        job.finished_at = timezone.now()
        await save_job(job)

def run_bot_task(job_id):
    asyncio.run(run_seo_bot(job_id))
