# crawler/page_visit.py - نسخه کامل و اصلاح شده

import random
import asyncio
from urllib.parse import urlparse
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from typing import Optional, List, Dict

from core.logger import logger
from human.behavior import random_interactions, human_reading_behavior
from human.actions import scroll_page_naturally, random_page_interactions
from crawler.link_extractor import extract_internal_links


async def smart_click_and_visit(
    page: Page, search_results: List[Dict], target_domain: str, search_engine_url: str
) -> bool:
    """
    کلیک واقعی روی نتایج جستجو با رفتار 100% انسانی

    Args:
        page: صفحه Playwright
        search_results: لیست Dict شامل {'rank', 'url', 'title', 'selector', 'element'}
        target_domain: دامنه هدف (مثلاً drshakibavida.com)
        search_engine_url: URL صفحه جستجو برای بازگشت

    Returns:
        True اگر حداقل یک بازدید موفق بود

    ✅ ویژگی‌های کلیدی:
    - کلیک واقعی روی DOM element
    - حرکت موس با منحنی Bezier
    - تأیید navigation با expect_navigation
    - بررسی document.readyState
    - رفتار کاملاً انسانی
    """
    visited_any = False

    try:
        # ═══════════════════════════════════════════════════════════
        # مرحله 1: فیلتر نتایج مربوط به target_domain
        # ═══════════════════════════════════════════════════════════
        target_results = []

        for result in search_results:
            result_url = result.get("url", "")
            if not result_url:
                continue

            try:
                parsed = urlparse(result_url)

                # بررسی اینکه URL از target_domain است
                if parsed.netloc.lower().endswith(target_domain.lower()):
                    target_results.append(result)
            except Exception as e:
                logger.debug(f"خطا در parse کردن URL {result_url}: {e}")
                continue

        if not target_results:
            logger.warning(f"⚠️ هیچ نتیجه‌ای از {target_domain} یافت نشد")
            return False

        logger.info(f"🎯 {len(target_results)} نتیجه از {target_domain} پیدا شد")

        # ═══════════════════════════════════════════════════════════
        # مرحله 2: انتخاب تصادفی 1-3 نتیجه
        # ═══════════════════════════════════════════════════════════
        num_to_click = min(random.randint(1, 3), len(target_results))
        selected = random.sample(target_results, num_to_click)

        logger.info(f"📋 {num_to_click} نتیجه برای کلیک انتخاب شد")

        # ═══════════════════════════════════════════════════════════
        # مرحله 3: پردازش هر نتیجه
        # ═══════════════════════════════════════════════════════════
        for i, result in enumerate(selected, 1):
            try:
                result_url = result.get("url", "")
                result_title = result.get("title", "بدون عنوان")
                result_rank = result.get("rank", "?")
                element = result.get("element")

                logger.info(f"\n{'='*70}")
                logger.info(f"🎯 نتیجه {i}/{num_to_click} (رتبه {result_rank})")
                logger.info(f"📌 عنوان: {result_title[:60]}")
                logger.info(f"🔗 URL: {result_url}")
                logger.info(f"{'='*70}")

                # ─────────────────────────────────────────────────────
                # گام 1: خواندن عنوان (رفتار انسانی)
                # ─────────────────────────────────────────────────────
                read_time = random.uniform(2, 5)
                logger.debug(f"📖 شبیه‌سازی خواندن عنوان ({read_time:.1f}s)...")
                await asyncio.sleep(read_time)

                # ─────────────────────────────────────────────────────
                # گام 2: کلیک روی المان (اگر موجود باشد)
                # ─────────────────────────────────────────────────────
                click_success = False

                if element:
                    try:
                        # بررسی اینکه المان هنوز در DOM است و visible است
                        is_visible = await element.is_visible()

                        if is_visible:
                            logger.debug("🎯 المان قابل مشاهده است، شروع کلیک...")

                            # اسکرول آهسته به المان
                            await element.scroll_into_view_if_needed()
                            await asyncio.sleep(random.uniform(0.8, 1.5))

                            # حرکت موس به المان با منحنی طبیعی
                            box = await element.bounding_box()
                            if box:
                                # محاسبه نقطه هدف (وسط المان + offset تصادفی)
                                target_x = (
                                    box["x"]
                                    + box["width"] / 2
                                    + random.randint(-20, 20)
                                )
                                target_y = (
                                    box["y"] + box["height"] / 2 + random.randint(-5, 5)
                                )

                                # گرفتن موقعیت فعلی موس (یا استفاده از مقدار پیش‌فرض)
                                try:
                                    current_pos = await page.evaluate("""
                                        () => {
                                            return {
                                                x: window.lastMouseX || 100,
                                                y: window.lastMouseY || 100
                                            };
                                        }
                                    """)
                                except:
                                    current_pos = {"x": 100, "y": 100}

                                # حرکت موس با منحنی Bezier (غیرخطی)
                                steps = random.randint(20, 35)
                                logger.debug(f"🖱️ حرکت موس در {steps} مرحله...")

                                for step in range(steps):
                                    progress = (step + 1) / steps

                                    # منحنی easeInOutQuad برای حرکت طبیعی‌تر
                                    if progress < 0.5:
                                        curve = 2 * progress * progress
                                    else:
                                        curve = 1 - pow(-2 * progress + 2, 2) / 2

                                    # محاسبه موقعیت با منحنی
                                    x = (
                                        current_pos["x"]
                                        + (target_x - current_pos["x"]) * curve
                                    )
                                    y = (
                                        current_pos["y"]
                                        + (target_y - current_pos["y"]) * curve
                                    )

                                    # اضافه کردن jitter (لرزش طبیعی)
                                    if random.random() < 0.1:
                                        x += random.uniform(-2, 2)
                                        y += random.uniform(-2, 2)

                                    await page.mouse.move(x, y)

                                    # ذخیره موقعیت برای استفاده بعدی
                                    await page.evaluate(f"""
                                        () => {{
                                            window.lastMouseX = {x};
                                            window.lastMouseY = {y};
                                        }}
                                    """)

                                    # تاخیر کوچک بین حرکات
                                    await asyncio.sleep(random.uniform(0.008, 0.025))

                            # هاور روی المان
                            logger.debug("🎯 هاور روی المان...")
                            await element.hover()
                            await asyncio.sleep(random.uniform(0.5, 1.5))

                            # کلیک واقعی با تأیید navigation
                            logger.info("🖱️ کلیک واقعی...")

                            try:
                                # استفاده از expect_navigation برای catch کردن navigation
                                async with page.expect_navigation(
                                    timeout=45000, wait_until="domcontentloaded"
                                ):
                                    await element.click()
                                    logger.debug(
                                        "✅ کلیک انجام شد، منتظر navigation..."
                                    )

                                click_success = True

                            except PlaywrightTimeout:
                                logger.warning("⏱️ Timeout در navigation بعد از کلیک")
                                click_success = False
                            except Exception as click_err:
                                logger.warning(f"⚠️ خطا در کلیک: {click_err}")
                                click_success = False

                        else:
                            logger.warning("⚠️ المان دیگر visible نیست")

                    except Exception as e:
                        logger.warning(f"⚠️ خطا در پردازش المان: {e}")

                # ─────────────────────────────────────────────────────
                # گام 3: Fallback به goto اگر کلیک ناموفق بود
                # ─────────────────────────────────────────────────────
                if not click_success:
                    logger.info("🔄 استفاده از navigation مستقیم...")

                    try:
                        await page.goto(
                            result_url, wait_until="networkidle", timeout=45000
                        )
                        click_success = True
                    except PlaywrightTimeout:
                        logger.error(f"⏱️ Timeout در goto به {result_url}")
                        continue
                    except Exception as goto_err:
                        logger.error(f"❌ خطا در goto: {goto_err}")
                        continue

                # ─────────────────────────────────────────────────────
                # گام 4: تأیید navigation موفق
                # ─────────────────────────────────────────────────────
                await asyncio.sleep(random.uniform(2, 4))

                current_url = page.url
                current_domain = urlparse(current_url).netloc.lower()

                if not current_domain.endswith(target_domain.lower()):
                    logger.warning(f"⚠️ به صفحه هدف نرسیدیم!")
                    logger.debug(f"URL فعلی: {current_url}")
                    logger.debug(f"Domain فعلی: {current_domain}")
                    logger.debug(f"Domain مورد انتظار: {target_domain}")

                    # برگشت به صفحه جستجو
                    await page.goto(search_engine_url, timeout=30000)
                    await asyncio.sleep(random.uniform(2, 4))
                    continue

                logger.info(f"✅ Navigation موفق به {target_domain}")

                # ─────────────────────────────────────────────────────
                # گام 5: بررسی بارگذاری کامل صفحه
                # ─────────────────────────────────────────────────────
                logger.debug("⏳ بررسی بارگذاری کامل صفحه...")

                try:
                    # بررسی document.readyState
                    ready_state = await page.evaluate("() => document.readyState")
                    logger.debug(f"📄 Document state: {ready_state}")

                    if ready_state != "complete":
                        await page.wait_for_load_state("load", timeout=15000)
                        logger.debug("✅ صفحه کامل بارگذاری شد")

                    # صبر کوتاه برای اجرای JavaScript
                    await asyncio.sleep(random.uniform(1.5, 3.0))

                except Exception as load_err:
                    logger.warning(f"⚠️ خطا در بررسی load state: {load_err}")
                    # ادامه می‌دهیم حتی اگر خطا داشتیم

                # ─────────────────────────────────────────────────────
                # گام 6: رفتار انسانی در صفحه
                # ─────────────────────────────────────────────────────
                logger.info("🎭 شروع رفتار طبیعی در صفحه...")

                # 6.1: اسکرول اولیه
                logger.debug("📜 اسکرول اولیه...")
                await scroll_page_naturally(page)

                # 6.2: خواندن محتوا (10-30 ثانیه)
                reading_time = random.uniform(12, 30)
                logger.debug(f"📖 شبیه‌سازی خواندن برای {reading_time:.1f} ثانیه...")
                await human_reading_behavior(page, duration_seconds=reading_time)

                # 6.3: تعاملات تصادفی (80% شانس)
                if random.random() < 0.8:
                    logger.debug("🖱️ تعاملات تصادفی (کلیک، هاور، موس)...")
                    await random_interactions(page)

                # 6.4: بازدید لینک‌های داخلی (70% شانس)
                if random.random() < 0.7:
                    logger.info("🔗 شروع بازدید لینک‌های داخلی...")

                    num_internal = random.randint(1, 3)
                    internal_visited = await visit_internal_links(
                        page, current_url, target_domain, max_links=num_internal
                    )

                    logger.info(f"📊 {internal_visited} لینک داخلی بازدید شد")

                # 6.5: اسکرول نهایی
                if random.random() < 0.5:
                    logger.debug("📜 اسکرول نهایی...")
                    await scroll_page_naturally(page)

                # 6.6: توقف نهایی قبل از خروج
                final_wait = random.uniform(3, 8)
                logger.debug(f"⏸️ توقف نهایی {final_wait:.1f}s...")
                await asyncio.sleep(final_wait)

                visited_any = True
                logger.info(f"✅ بازدید کامل از نتیجه {i} انجام شد")

                # ─────────────────────────────────────────────────────
                # گام 7: بازگشت به موتور جستجو
                # ─────────────────────────────────────────────────────
                logger.info("🔙 بازگشت به موتور جستجو...")

                try:
                    await page.goto(
                        search_engine_url, wait_until="domcontentloaded", timeout=30000
                    )
                    await asyncio.sleep(random.uniform(3, 6))
                    logger.debug("✅ بازگشت موفق")

                except Exception as back_err:
                    logger.warning(f"⚠️ خطا در بازگشت: {back_err}")
                    # اگر بازگشت ناموفق بود، ادامه نمی‌دهیم
                    break

                # ─────────────────────────────────────────────────────
                # تاخیر بین نتایج
                # ─────────────────────────────────────────────────────
                if i < num_to_click:
                    delay = random.uniform(10, 20)
                    logger.info(f"⏳ تاخیر {delay:.1f}s تا نتیجه بعدی...")
                    await asyncio.sleep(delay)

            except Exception as result_err:
                logger.error(f"❌ خطا در پردازش نتیجه {i}: {result_err}", exc_info=True)

                # تلاش برای بازگشت به موتور جستجو
                try:
                    await page.goto(search_engine_url, timeout=30000)
                    await asyncio.sleep(random.uniform(2, 4))
                except Exception:
                    logger.error("❌ نمی‌توان به صفحه جستجو بازگشت")
                    break

                continue

        # ═══════════════════════════════════════════════════════════
        # نتیجه نهایی
        # ═══════════════════════════════════════════════════════════
        if visited_any:
            logger.info(f"✅ حداقل یک بازدید موفق انجام شد")
        else:
            logger.warning(f"⚠️ هیچ بازدید موفقی انجام نشد")

        return visited_any

    except Exception as e:
        logger.error(f"❌ خطای کلی در smart_click_and_visit: {e}", exc_info=True)
        return visited_any


async def visit_page_naturally(
    page: Page, url: str, target_domain: str, is_from_search: bool = False
) -> bool:
    """
    بازدید طبیعی از یک صفحه با تأیید بارگذاری کامل

    Args:
        page: صفحه Playwright
        url: URL مقصد
        target_domain: دامنه هدف
        is_from_search: آیا از نتایج جستجو آمده؟

    Returns:
        True اگر موفق، False در غیر این صورت

    ✅ ویژگی‌ها:
    - wait_until="networkidle" برای بارگذاری کامل
    - بررسی document.readyState
    - رفتار خواندن انسانی
    - اسکرول طبیعی
    """
    try:
        logger.info(f"🌐 بازدید طبیعی از: {url[:80]}...")

        # ═══════════════════════════════════════════════════════════
        # مرحله 1: Navigation به صفحه
        # ═══════════════════════════════════════════════════════════
        try:
            response = await page.goto(
                url,
                wait_until="networkidle",  # منتظر می‌ماند تا network idle شود
                timeout=45000,
            )

            if not response:
                logger.warning(f"⚠️ هیچ response دریافت نشد")
                return False

            if response.status >= 400:
                logger.warning(f"⚠️ خطای HTTP {response.status}")
                return False

            logger.debug(f"✅ Response status: {response.status}")

        except PlaywrightTimeout:
            logger.warning(f"⏱️ Timeout در navigation به {url}")
            return False
        except Exception as nav_err:
            logger.error(f"❌ خطا در navigation: {nav_err}")
            return False

        # ═══════════════════════════════════════════════════════════
        # مرحله 2: بررسی بارگذاری کامل
        # ═══════════════════════════════════════════════════════════
        try:
            # بررسی load state
            await page.wait_for_load_state("load", timeout=10000)

            # بررسی document.readyState
            ready_state = await page.evaluate("() => document.readyState")
            logger.debug(f"📄 Document state: {ready_state}")

            # صبر اضافی برای JavaScript
            await asyncio.sleep(random.uniform(2, 4))

        except Exception as load_err:
            logger.warning(f"⚠️ خطا در بررسی load: {load_err}")
            # ادامه می‌دهیم

        # ═══════════════════════════════════════════════════════════
        # مرحله 3: رفتار انسانی
        # ═══════════════════════════════════════════════════════════

        # 3.1: اسکرول اولیه
        logger.debug("📜 اسکرول اولیه...")
        await scroll_page_naturally(page)

        # 3.2: خواندن محتوا
        if is_from_search:
            reading_duration = random.uniform(12, 30)
        else:
            reading_duration = random.uniform(8, 20)

        logger.debug(f"📖 خواندن برای {reading_duration:.1f} ثانیه...")
        await human_reading_behavior(page, reading_duration)

        # 3.3: تعاملات تصادفی (70% شانس)
        if random.random() < 0.7:
            logger.debug("🖱️ تعاملات تصادفی...")
            await random_interactions(page)

        # 3.4: اسکرول نهایی (50% شانس)
        if random.random() < 0.5:
            logger.debug("📜 اسکرول نهایی...")
            await scroll_page_naturally(page)

        # 3.5: توقف نهایی
        final_wait = random.uniform(3, 8)
        logger.debug(f"⏸️ توقف نهایی {final_wait:.1f}s...")
        await asyncio.sleep(final_wait)

        logger.info(f"✅ بازدید موفق از {url[:60]}...")
        return True

    except Exception as e:
        logger.error(f"❌ خطا در visit_page_naturally: {e}", exc_info=True)
        return False


async def visit_internal_links(
    page: Page, current_url: str, target_domain: str, max_links: int = 3
) -> int:
    """
    بازدید از لینک‌های داخلی با رفتار طبیعی

    Args:
        page: صفحه Playwright
        current_url: URL صفحه فعلی
        target_domain: دامنه هدف
        max_links: حداکثر تعداد لینک‌ها

    Returns:
        تعداد لینک‌هایی که با موفقیت بازدید شدند
    """
    visited_count = 0

    try:
        logger.info(f"🔗 استخراج لینک‌های داخلی از {current_url[:60]}...")

        # ═══════════════════════════════════════════════════════════
        # مرحله 1: استخراج لینک‌های داخلی
        # ═══════════════════════════════════════════════════════════
        internal_links = await extract_internal_links(
            page, current_url, target_domain, max_links=50  # استخراج بیشتر، انتخاب کمتر
        )

        if not internal_links:
            logger.debug("⚠️ هیچ لینک داخلی یافت نشد")
            return 0

        logger.info(f"📋 {len(internal_links)} لینک داخلی استخراج شد")

        # ═══════════════════════════════════════════════════════════
        # مرحله 2: انتخاب تصادفی
        # ═══════════════════════════════════════════════════════════
        num_to_visit = min(max_links, len(internal_links))
        selected_links = random.sample(internal_links, num_to_visit)

        logger.info(f"🎯 {num_to_visit} لینک برای بازدید انتخاب شد")

        # ═══════════════════════════════════════════════════════════
        # مرحله 3: بازدید از لینک‌ها
        # ═══════════════════════════════════════════════════════════
        for i, link in enumerate(selected_links, 1):
            # تاخیر بین بازدید لینک‌ها
            if i > 1:
                delay = random.uniform(5, 12)
                logger.debug(f"⏳ تاخیر {delay:.1f}s قبل از لینک {i}...")
                await asyncio.sleep(delay)

            logger.info(f"\n🔗 لینک داخلی {i}/{num_to_visit}: {link[:60]}...")

            # بازدید از لینک
            success = await visit_page_naturally(
                page, link, target_domain, is_from_search=False
            )

            if success:
                visited_count += 1
                logger.debug(f"✅ بازدید موفق از لینک {i}")

                # شانس بازدید از لینک‌های تو در تو (فقط برای اولین لینک)
                if i == 1 and random.random() < 0.3:
                    logger.debug("🔄 بررسی لینک‌های تو در تو...")

                    nested_count = await visit_internal_links(
                        page, link, target_domain, max_links=1
                    )

                    visited_count += nested_count

                    if nested_count > 0:
                        logger.info(f"✅ {nested_count} لینک تو در تو بازدید شد")
            else:
                logger.warning(f"⚠️ بازدید از لینک {i} ناموفق بود")

        logger.info(f"✅ مجموع {visited_count} لینک داخلی بازدید شد")
        return visited_count

    except Exception as e:
        logger.error(f"❌ خطا در visit_internal_links: {e}", exc_info=True)
        return visited_count
