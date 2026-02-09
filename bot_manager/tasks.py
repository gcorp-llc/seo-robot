import asyncio
import random
from django.utils import timezone
from playwright.async_api import async_playwright
from bot_manager.models import BotJob, SiteConfig, Keyword, SearchEngine, Proxy, Device, CrawledLink
from crawler.link_extractor import extract_internal_links
from crawler.search_engine import perform_search
from crawler.page_visit import visit_page_naturally, smart_click_and_visit
from urllib.parse import urlparse

async def run_seo_bot(job_id):
    job = BotJob.objects.get(id=job_id)
    job.status = 'running'
    job.save()

    def add_log(msg):
        timestamp = timezone.now().strftime("%H:%M:%S")
        job.log += f"[{timestamp}] {msg}\n"
        job.save()

    try:
        add_log(f"شروع عملیات برای سایت: {job.site.name}")
        job.progress = 10
        job.current_step = "آماده‌سازی مرورگر"
        job.save()

        # انتخاب پروکسی تصادفی فعال
        active_proxies = Proxy.objects.filter(is_active=True)
        proxy = random.choice(active_proxies).url if active_proxies.exists() else None

        # انتخاب دستگاه تصادفی
        active_devices = Device.objects.filter(is_active=True)
        device_config = random.choice(active_devices).config_json if active_devices.exists() else {}

        async with async_playwright() as p:
            browser_args = []
            if proxy:
                add_log(f"استفاده از پروکسی: {proxy}")

            browser = await p.chromium.launch(headless=True, args=browser_args)
            context = await browser.new_context(**device_config)
            page = await context.new_page()

            # مرحله 1: کرال بخش مقالات
            job.progress = 20
            job.current_step = "کرال بخش مقالات"
            job.save()
            add_log(f"مراجعه به بخش مقالات: {job.site.articles_url}")

            await page.goto(job.site.articles_url, wait_until="networkidle")
            domain = urlparse(job.site.main_url).netloc
            links = await extract_internal_links(page, job.site.articles_url, domain)

            add_log(f"تعداد {len(links)} لینک استخراج شد.")

            # ذخیره لینک‌ها
            stored_links = []
            for link_url in links:
                obj, created = CrawledLink.objects.get_or_create(site=job.site, url=link_url)
                stored_links.append(obj)

            # مرحله 2: بازدید از مقالات کرال شده
            job.progress = 40
            job.current_step = "بازدید از مقالات"
            job.save()

            visit_count = min(len(stored_links), 3)
            links_to_visit = random.sample(stored_links, visit_count)

            for i, link_obj in enumerate(links_to_visit):
                add_log(f"بازدید از مقاله {i+1}/{visit_count}: {link_obj.url}")
                success = await visit_page_naturally(page, link_obj.url, domain)
                if success:
                    link_obj.is_visited = True
                    link_obj.save()
                await asyncio.sleep(random.uniform(2, 5))

            # مرحله 3: جستجو در موتورهای جستجو (اگر فعال باشد)
            if job.site.search_engines_enabled:
                job.progress = 60
                job.current_step = "جستجو در موتورهای جستجو"
                job.save()

                keywords = job.site.keywords.all()
                active_engines = SearchEngine.objects.filter(is_active=True)

                if keywords.exists() and active_engines.exists():
                    keyword = random.choice(keywords).word
                    engine = random.choice(active_engines).name
                    add_log(f"جستجوی کلمه '{keyword}' در {engine}")

                    search_results = await perform_search(page, engine, keyword)
                    if search_results:
                        add_log(f"تعداد {len(search_results)} نتیجه یافت شد. در حال یافتن سایت هدف...")
                        found = await smart_click_and_visit(page, search_results, domain, page.url)
                        if found:
                            add_log("سایت هدف در نتایج یافت و بازدید شد.")
                        else:
                            add_log("سایت هدف در نتایج صفحه اول یافت نشد.")
                else:
                    add_log("کلمه کلیدی یا موتور جستجوی فعال یافت نشد.")

            # مرحله نهایی: بازدید مستقیم
            job.progress = 90
            job.current_step = "بازدید مستقیم نهایی"
            job.save()
            add_log(f"بازدید مستقیم از صفحه اصلی: {job.site.main_url}")
            await visit_page_naturally(page, job.site.main_url, domain)

            await browser.close()

        job.status = 'completed'
        job.progress = 100
        job.finished_at = timezone.now()
        job.current_step = "تکمیل شده"
        add_log("عملیات با موفقیت به پایان رسید.")
        job.save()

    except Exception as e:
        import traceback
        error_msg = f"خطا در اجرای عملیات: {str(e)}\n{traceback.format_exc()}"
        add_log(error_msg)
        job.status = 'failed'
        job.finished_at = timezone.now()
        job.save()

def run_bot_task(job_id):
    asyncio.run(run_seo_bot(job_id))
