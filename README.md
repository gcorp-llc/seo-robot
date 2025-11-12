# ربات SEO پیشرفته — شبیه‌سازی بازدید انسانی

این پروژه یک ربات هوشمند SEO است که با استفاده از Playwright مرورگر را به صورت خودکار کنترل می‌کند. هدف شبیه‌سازی رفتار انسانی واقعی برای تعامل با موتورهای جستجو و بازدید صفحات است.

> هشدار: فقط برای استفاده قانونی و با رعایت قوانین سایت‌ها و قوانین محلی استفاده شود.

---

## ویژگی‌های کلیدی
- موتورهای جستجو: Google, Bing, DuckDuckGo, Yandex, Yahoo, Brave, Ecosia, Startpage
- شبیه‌سازی انسانی: حرکت موس، اسکرول طبیعی، کلیک تصادفی، تأخیر هوشمند
- مدیریت پروکسی: بارگذاری از CSV، بررسی سلامت، چرخش خودکار، علامت‌گذاری شکست
- شبیه‌سازی دستگاه: iPhone, Pixel, Galaxy با تنظیمات واقعی
- کرال عمیق: استخراج و بازدید لینک‌های داخلی تا عمق مشخص
- استراتژی‌های جایگزین: استخراج URL از متن، متا، اسکریپت، تصویر در صورت عدم کارکرد سلکتور
- مانیتورینگ عملکرد: آمار موفقیت، زمان، خطا، گزارش JSON
- سیستم لاگ پیشرفته: Rotating File Handlers
- پیکربندی ماژولار: تنظیمات در پوشه `config/`

---

## نصب و راه‌اندازی

1. کلون مخزن و ورود به پوشه پروژه:
    ```bash
    git clone <آدرس-مخزن>
    cd seo-bot
    ```

2. نصب وابستگی‌ها (Python 3.10+):
    ```bash
    pip install -r requirements.txt
    ```

# 3. نصب مرورگرهای Playwright
playwright install

# 4. قرار دادن فایل پروکسی
# فایل proxies-export.csv را در ریشه پروژه قرار دهید
# ستون‌ها: IP, Port, Protocol, Country, Latency

فایل .env (اختیاری)

HEADLESS=true
LOG_LEVEL=INFO
USE_PROXY_ROTATION=true
INCLUDE_NO_PROXY=false
MAX_RESULTS_TO_CHECK=30

نحوه اجرا
bashpython main.py
تمام لاگ‌ها در پوشه logs/ ذخیره می‌شوند.
گزارش عملکرد در فایل performance_report_*.json ذخیره می‌شود.

## نقشه فایل‌ها و پوشه‌ها (Project Structure)

```
seo-bot/
├── main.py                        # نقطه ورود برنامه
├── proxies-export.csv             # لیست پروکسی‌ها (IP,Port,Protocol,Country,Latency)
├── README.md                      # راهنمای پروژه
├── requirements.txt               # وابستگی‌ها
├── config/
│   ├── __init__.py                # صادرات تنظیمات
│   ├── main_config.py             # بارگذاری .env و تنظیمات عمومی
│   ├── proxy_config.py            # ProxyType, ProxyConfig, ProxyManager
│   ├── proxy_loader.py            # بارگذاری و فیلتر پروکسی از CSV
│   ├── search_engines.py          # تنظیمات موتورهای جستجو و سلکتورها
│   ├── targets.py                 # TARGETS، کوئری‌ها و URLها
│   ├── human_settings.py          # تنظیمات رفتار انسانی
│   └── general_settings.py        # HEADLESS، TIMEOUT، DEVICES، USER-AGENTS
├── core/
│   ├── __init__.py
│   ├── logger.py                  # راه‌اندازی لاگینگ (RotatingFileHandler)
│   ├── error_handler.py           # مدیریت خطا و retry
│   ├── performance_monitor.py     # آمار و گزارش‌گیری
│   └── utils.py                   # توابع کمکی
├── browser/
│   ├── __init__.py
│   ├── pool.py                    # استخر مرورگر (reuse, cleanup)
│   └── launcher.py                # راه‌اندازی مرورگر با پروکسی و آرگومان‌ها
├── crawler/
│   ├── __init__.py
│   ├── search_engine.py           # جستجو در موتور و استخراج نتایج
│   ├── page_visit.py              # بازدید طبیعی صفحات (اسکرول، کلیک، تعامل)
│   ├── link_extractor.py          # استخراج لینک‌های داخلی
│   ├── fallback_extractors.py     # استخراج از متن/متا/اسکریپت/تصاویر
│   └── interceptors.py            # مسدودسازی منابع غیرضروری
├── devices/
│   ├── __init__.py
│   └── processor.py               # پردازش هر دستگاه: context, tracing, scenarios
├── human/
│   ├── behavior.py                # حرکت موس، کلیک‌های انسانی
│   ├── captcha.py                 # مدیریت CAPTCHA
│   └── actions.py                 # اسکرول و تعاملات
├── network/
│   ├── proxy_checker.py           # بررسی سلامت پروکسی‌ها (httpbin، کش)
│   ├── proxy_selector.py          # انتخاب پروکسی بر اساس معیارها
│   └── proxy_utils.py             # ساخت و اعتبارسنجی پروکسی از CSV
└── logs/
    ├── seo_bot.log
    ├── seo_bot_errors.log
    ├── seo_bot_debug.log
    └── seo_bot_performance.log
```

---

## نکات مهم
- فایل `proxies-export.csv` باید در ریشه پروژه باشد.
- از پروکسی‌های با کیفیت و با تأخیر کم استفاده کنید.
- برای تست محلی از `HEADLESS=false` استفاده کنید تا مرورگر قابل مشاهده باشد.
- اجرای بی‌رویه و بدون رعایت قوانین سایت‌ها ممکن است منجر به بلاک شدن یا پیامدهای قانونی شود.

---

## وابستگی‌ها (مختصر)
- playwright
- aiohttp
- python-dotenv (اختیاری)

نصب:
```bash
pip install -r requirements.txt
playwright install
```

---

## مجوز
MIT — استفاده مسئولانه و قانونی الزامی است.

