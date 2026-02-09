"""
تست سریع پروکسی‌ها برای دیباگ
"""

import asyncio
import aiohttp
from datetime import datetime

# لیست پروکسی‌های شما (فرمت: "http://IP:PORT")
PROXIES = [
    "http://3.87.76.58:1080",
    "http://209.97.150.167:80",
    "http://44.251.173.250:9106",
    "http://138.68.60.8:3128",
    "http://3.87.76.58:80",
    "http://47.90.149.238:8889",
    "http://47.90.149.238:8443",
    "http://47.90.149.238:4145",
    "http://47.252.11.233:45",
]


async def test_proxy(proxy_url: str) -> dict:
    """تست یک پروکسی"""
    result = {"proxy": proxy_url, "status": "❌ Failed", "error": "", "time": 0}

    try:
        start = asyncio.get_event_loop().time()
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "http://httpbin.org/ip", proxy=proxy_url, ssl=False
            ) as resp:
                end = asyncio.get_event_loop().time()
                result["time"] = round((end - start) * 1000, 2)

                if resp.status == 200:
                    data = await resp.json()
                    result["status"] = "✅ Working"
                    result["ip"] = data.get("origin", "Unknown")
                    print(f"✅ {proxy_url} - {result['time']}ms - IP: {result['ip']}")
                else:
                    result["error"] = f"Status {resp.status}"
                    print(f"⚠️  {proxy_url} - Status: {resp.status}")

    except asyncio.TimeoutError:
        result["error"] = "Timeout"
        print(f"⏰ {proxy_url} - Timeout")
    except aiohttp.ClientProxyConnectionError as e:
        result["error"] = f"Proxy Error: {str(e)[:50]}"
        print(f"❌ {proxy_url} - Proxy Error: {str(e)[:50]}")
    except Exception as e:
        result["error"] = str(e)[:100]
        print(f"❌ {proxy_url} - Error: {str(e)[:50]}")

    return result


async def test_all():
    """تست همه پروکسی‌ها"""
    print("=" * 70)
    print("🧪 شروع تست پروکسی‌ها...")
    print("=" * 70)

    # تست با HTTP
    print("\n📡 تست با پروتکل HTTP:")
    print("-" * 70)
    http_results = await asyncio.gather(*[test_proxy(proxy) for proxy in PROXIES])

    # شمارش نتایج
    working = sum(1 for r in http_results if "✅" in r["status"])

    print("\n" + "=" * 70)
    print(f"📊 نتیجه: {working} از {len(PROXIES)} پروکسی کار می‌کند")
    print("=" * 70)

    # نمایش پروکسی‌های کاربردی
    if working > 0:
        print("\n✅ پروکسی‌های کاربردی:")
        for r in http_results:
            if "✅" in r["status"]:
                print(f"  • {r['proxy']} - {r['time']}ms - {r.get('ip', 'N/A')}")
    else:
        print("\n❌ هیچ پروکسی کاربردی یافت نشد!")
        print("\n💡 دلایل احتمالی:")
        print("  1. پروکسی‌ها expire شده‌اند (پروکسی‌های رایگان عمر کوتاهی دارند)")
        print("  2. فایروال یا فیلترینگ شبکه")
        print("  3. پروکسی‌ها به درخواست‌های Python پاسخ نمی‌دهند")

        print("\n🔧 راه‌حل‌های پیشنهادی:")
        print("  • از سرویس‌های پروکسی پولی استفاده کنید")
        print("  • از SOCKS5 به جای HTTP استفاده کنید")
        print("  • با گزینه INCLUDE_NO_PROXY=true بدون پروکسی تست کنید")


async def test_with_playwright():
    """تست با Playwright برای مقایسه"""
    print("\n\n" + "=" * 70)
    print("🎭 تست با Playwright (مثل کد اصلی):")
    print("=" * 70)

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # تست اولین پروکسی
            proxy_url = PROXIES[0]

            print(f"\n🔍 تست {proxy_url} با Playwright...")

            try:
                browser = await p.chromium.launch(
                    headless=True,
                    proxy={"server": proxy_url},
                    args=["--ignore-certificate-errors"],
                )

                context = await browser.new_context(ignore_https_errors=True)
                page = await context.new_page()

                await page.goto("http://httpbin.org/ip", timeout=15000)
                content = await page.content()

                if "origin" in content:
                    print(f"✅ Playwright با {proxy_url} کار کرد!")
                else:
                    print(f"⚠️  Playwright به {proxy_url} متصل شد اما محتوا صحیح نیست")

                await browser.close()

            except Exception as e:
                print(f"❌ Playwright با {proxy_url} کار نکرد: {str(e)[:100]}")

    except ImportError:
        print("⚠️  Playwright نصب نیست، این بخش skip شد")


async def main():
    """تابع اصلی"""
    # تست با aiohttp
    await test_all()

    # تست با Playwright
    await test_with_playwright()

    print("\n" + "=" * 70)
    print("✅ تست کامل شد!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
