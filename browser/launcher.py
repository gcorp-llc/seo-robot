# browser/launcher.py - نسخه کامل با Anti-Detection پیشرفته

from typing import Optional, Dict, Any
from playwright.async_api import Playwright, Browser, BrowserContext
from network.proxy_config_model import ProxyConfig
from config.general_settings import HEADLESS
from core.logger import logger


async def launch_browser_with_proxy(
    playwright: Playwright, proxy_config: Optional[ProxyConfig] = None
) -> Browser:
    """
    راه‌اندازی مرورگر Chromium با تنظیمات Anti-Detection پیشرفته

    Args:
        playwright: نمونه Playwright
        proxy_config: پیکربندی پروکسی (اختیاری)

    Returns:
        Browser: نمونه مرورگر راه‌اندازی شده

    ✅ ویژگی‌های کلیدی:
    - حذف تمام علائم automation
    - استفاده از channel="chrome" برای fingerprint طبیعی
    - آرگومان‌های بهینه شده برای عدم شناسایی
    - پشتیبانی از پروکسی با authentication
    """

    # ═══════════════════════════════════════════════════════════════
    # آرگومان‌های مرورگر (بدون علائم bot)
    # ═══════════════════════════════════════════════════════════════
    browser_args = [
        # ✅ مهم‌ترین: حذف AutomationControlled
        "--disable-blink-features=AutomationControlled",
        # ✅ امنیت و sandbox
        "--no-sandbox",
        "--disable-setuid-sandbox",
        # ✅ بهینه‌سازی منابع
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--disable-gpu",
        # ✅ رفتار طبیعی‌تر
        "--no-first-run",
        "--no-zygote",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-infobars",
        "--disable-breakpad",
        # ✅ اندازه پنجره واقعی
        "--window-size=1920,1080",
        # ✅ غیرفعال‌سازی extension‌ها
        "--disable-extensions",
        "--disable-component-extensions-with-background-pages",
        # ✅ rendering طبیعی
        "--font-render-hinting=none",
        "--disable-features=TranslateUI",
        "--disable-features=BlinkGenPropertyTrees",
        # ✅ network
        "--disable-ipc-flooding-protection",
        "--disable-background-networking",
        # ✅ برای پروکسی
        "--proxy-bypass-list=<-loopback>",
        # ✅ جلوگیری از leak
        "--disable-features=AudioServiceOutOfProcess",
        "--disable-features=IsolateOrigins",
        "--disable-site-isolation-trials",
        # ✅ WebRTC
        "--enforce-webrtc-ip-permission-check",
        "--force-webrtc-ip-handling-policy=default_public_interface_only",
    ]

    # ═══════════════════════════════════════════════════════════════
    # تنظیمات پروکسی
    # ═══════════════════════════════════════════════════════════════
    proxy_dict = None
    if proxy_config:
        proxy_dict = {
            "server": proxy_config.url,
        }

        # اضافه کردن username/password اگر موجود باشد
        if hasattr(proxy_config, "username") and proxy_config.username:
            proxy_dict["username"] = proxy_config.username
        if hasattr(proxy_config, "password") and proxy_config.password:
            proxy_dict["password"] = proxy_config.password

        logger.debug(f"🔌 پروکسی فعال: {proxy_config.url}")
    else:
        logger.debug("🔌 بدون پروکسی")

    # ═══════════════════════════════════════════════════════════════
    # راه‌اندازی مرورگر
    # ═══════════════════════════════════════════════════════════════
    try:
        browser = await playwright.chromium.launch(
            headless=HEADLESS,
            args=browser_args,
            proxy=proxy_dict,
            # ✅ حذف --enable-automation
            ignore_default_args=[
                "--enable-automation",
                "--enable-blink-features=AutomationControlled",
            ],
            # ✅ استفاده از Chrome واقعی (اگر موجود باشد)
            # این به fingerprint طبیعی‌تری کمک می‌کند
            channel="chrome",  # یا "msedge" برای Microsoft Edge
            # ✅ تنظیمات اضافی
            downloads_path=None,  # غیرفعال کردن دانلود خودکار
        )

        logger.info("✅ مرورگر با موفقیت راه‌اندازی شد")
        return browser

    except Exception as e:
        logger.error(f"❌ خطا در راه‌اندازی مرورگر: {e}")

        # ✅ Fallback: بدون channel="chrome"
        logger.warning("🔄 تلاش مجدد بدون channel...")

        try:
            browser = await playwright.chromium.launch(
                headless=HEADLESS,
                args=browser_args,
                proxy=proxy_dict,
                ignore_default_args=[
                    "--enable-automation",
                    "--enable-blink-features=AutomationControlled",
                ],
            )

            logger.info("✅ مرورگر با موفقیت راه‌اندازی شد (بدون channel)")
            return browser

        except Exception as fallback_err:
            logger.error(f"❌ خطا در fallback: {fallback_err}")
            raise


async def setup_stealth_context(browser: Browser, **context_kwargs) -> BrowserContext:
    """
    ساخت Browser Context با تنظیمات Anti-Detection کامل

    Args:
        browser: نمونه Browser
        **context_kwargs: آرگومان‌های اضافی برای new_context

    Returns:
        BrowserContext: context با stealth mode فعال

    ✅ این تابع 12 تکنیک Anti-Detection اعمال می‌کند:
    1. حذف navigator.webdriver
    2. Mock کردن window.chrome
    3. تغییر navigator.permissions
    4. Mock کردن navigator.plugins
    5. تغییر navigator.languages
    6. Mock کردن Battery API
    7. اضافه کردن noise به Canvas fingerprint
    8. تغییر WebGL fingerprint
    9. حذف cdc_* properties (Playwright detection)
    10. Mock کردن hardwareConcurrency
    11. Mock کردن deviceMemory
    12. Mock کردن navigator.connection

    استفاده:
        context = await setup_stealth_context(browser, user_agent="...")
        page = await context.new_page()
    """

    # ═══════════════════════════════════════════════════════════════
    # ساخت context با تنظیمات
    # ═══════════════════════════════════════════════════════════════
    context = await browser.new_context(**context_kwargs)

    logger.debug("🎭 اعمال تنظیمات Stealth...")

    # ═══════════════════════════════════════════════════════════════
    # اضافه کردن init script
    # ═══════════════════════════════════════════════════════════════
    await context.add_init_script("""
// ═══════════════════════════════════════════════════════════════
// Anti-Detection Script - اجرا می‌شود قبل از هر صفحه
// ═══════════════════════════════════════════════════════════════

(() => {
    'use strict';
    
    // ───────────────────────────────────────────────────────────
    // 1. حذف navigator.webdriver
    // ───────────────────────────────────────────────────────────
    try {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 2. Mock کردن window.chrome
    // ───────────────────────────────────────────────────────────
    try {
        if (!window.chrome) {
            window.chrome = {};
        }
        
        window.chrome.runtime = {
            PlatformOs: {
                MAC: 'mac',
                WIN: 'win',
                ANDROID: 'android',
                CROS: 'cros',
                LINUX: 'linux',
                OPENBSD: 'openbsd'
            },
            PlatformArch: {
                ARM: 'arm',
                X86_32: 'x86-32',
                X86_64: 'x86-64'
            },
            PlatformNaclArch: {
                ARM: 'arm',
                X86_32: 'x86-32',
                X86_64: 'x86-64'
            },
            RequestUpdateCheckStatus: {
                THROTTLED: 'throttled',
                NO_UPDATE: 'no_update',
                UPDATE_AVAILABLE: 'update_available'
            },
            OnInstalledReason: {
                INSTALL: 'install',
                UPDATE: 'update',
                CHROME_UPDATE: 'chrome_update',
                SHARED_MODULE_UPDATE: 'shared_module_update'
            },
            OnRestartRequiredReason: {
                APP_UPDATE: 'app_update',
                OS_UPDATE: 'os_update',
                PERIODIC: 'periodic'
            }
        };
        
        window.chrome.loadTimes = function() {
            return {
                commitLoadTime: Date.now() / 1000 - Math.random() * 10,
                connectionInfo: 'http/1.1',
                finishDocumentLoadTime: Date.now() / 1000,
                finishLoadTime: Date.now() / 1000,
                firstPaintAfterLoadTime: 0,
                firstPaintTime: Date.now() / 1000 - Math.random(),
                navigationType: 'Other',
                npnNegotiatedProtocol: 'unknown',
                requestTime: Date.now() / 1000 - Math.random() * 10,
                startLoadTime: Date.now() / 1000 - Math.random() * 10,
                wasAlternateProtocolAvailable: false,
                wasFetchedViaSpdy: false,
                wasNpnNegotiated: false
            };
        };
        
        window.chrome.csi = function() {
            return {
                onloadT: Date.now(),
                pageT: Math.random() * 1000,
                startE: Date.now() - Math.random() * 1000,
                tran: 15
            };
        };
        
        window.chrome.app = {
            isInstalled: false,
            InstallState: {
                DISABLED: 'disabled',
                INSTALLED: 'installed',
                NOT_INSTALLED: 'not_installed'
            },
            RunningState: {
                CANNOT_RUN: 'cannot_run',
                READY_TO_RUN: 'ready_to_run',
                RUNNING: 'running'
            }
        };
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 3. تغییر navigator.permissions
    // ───────────────────────────────────────────────────────────
    try {
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 4. Mock کردن navigator.plugins
    // ───────────────────────────────────────────────────────────
    try {
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {
                        type: "application/x-google-chrome-pdf",
                        suffixes: "pdf",
                        description: "Portable Document Format",
                        enabledPlugin: Plugin
                    },
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {
                        type: "application/pdf",
                        suffixes: "pdf",
                        description: "Portable Document Format",
                        enabledPlugin: Plugin
                    },
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Viewer"
                },
                {
                    0: {
                        type: "application/x-nacl",
                        suffixes: "",
                        description: "Native Client Executable",
                        enabledPlugin: Plugin
                    },
                    1: {
                        type: "application/x-pnacl",
                        suffixes: "",
                        description: "Portable Native Client Executable",
                        enabledPlugin: Plugin
                    },
                    description: "",
                    filename: "internal-nacl-plugin",
                    length: 2,
                    name: "Native Client"
                }
            ],
            configurable: true
        });
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 5. تغییر navigator.languages
    // ───────────────────────────────────────────────────────────
    try {
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'fa-IR', 'fa'],
            configurable: true
        });
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 6. Mock کردن Battery API
    // ───────────────────────────────────────────────────────────
    try {
        if (navigator.getBattery) {
            const originalGetBattery = navigator.getBattery.bind(navigator);
            navigator.getBattery = async () => {
                const battery = await originalGetBattery();
                Object.defineProperty(battery, 'charging', { 
                    value: true,
                    writable: false
                });
                Object.defineProperty(battery, 'chargingTime', { 
                    value: 0,
                    writable: false
                });
                Object.defineProperty(battery, 'dischargingTime', { 
                    value: Infinity,
                    writable: false
                });
                Object.defineProperty(battery, 'level', { 
                    value: 1.0,
                    writable: false
                });
                return battery;
            };
        }
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 7. اضافه کردن noise به Canvas fingerprint
    // ───────────────────────────────────────────────────────────
    try {
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(...args) {
            const imageData = getImageData.apply(this, args);
            
            // اضافه کردن noise بسیار کم (1 در 100 پیکسل)
            for (let i = 0; i < imageData.data.length; i += 4) {
                if (Math.random() < 0.01) {
                    imageData.data[i] = Math.min(255, imageData.data[i] + 1);
                }
            }
            
            return imageData;
        };
        
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {
            return toDataURL.apply(this, args);
        };
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 8. تغییر WebGL fingerprint
    // ───────────────────────────────────────────────────────────
    try {
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.apply(this, [parameter]);
        };
        
        // همین کار را برای WebGL2 هم انجام بده
        if (window.WebGL2RenderingContext) {
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter2.apply(this, [parameter]);
            };
        }
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 9. حذف cdc_* properties (Playwright/ChromeDriver detection)
    // ───────────────────────────────────────────────────────────
    try {
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 10. Mock کردن hardwareConcurrency
    // ───────────────────────────────────────────────────────────
    try {
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
            configurable: true
        });
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 11. Mock کردن deviceMemory
    // ───────────────────────────────────────────────────────────
    try {
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true
        });
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // 12. Mock کردن navigator.connection
    // ───────────────────────────────────────────────────────────
    try {
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                effectiveType: '4g',
                downlink: 10,
                rtt: 50,
                saveData: false,
                type: 'wifi'
            }),
            configurable: true
        });
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // بونوس: Mock کردن mediaDevices
    // ───────────────────────────────────────────────────────────
    try {
        if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
            const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
            navigator.mediaDevices.enumerateDevices = async () => {
                const devices = await originalEnumerateDevices();
                return devices.map(device => ({
                    ...device,
                    deviceId: 'default',
                    groupId: 'default'
                }));
            };
        }
    } catch (e) {}
    
    // ───────────────────────────────────────────────────────────
    // بونوس: Mock کردن screen properties
    // ───────────────────────────────────────────────────────────
    try {
        Object.defineProperty(screen, 'availWidth', {
            get: () => screen.width,
            configurable: true
        });
        Object.defineProperty(screen, 'availHeight', {
            get: () => screen.height,
            configurable: true
        });
        Object.defineProperty(screen, 'availTop', {
            get: () => 0,
            configurable: true
        });
        Object.defineProperty(screen, 'availLeft', {
            get: () => 0,
            configurable: true
        });
    } catch (e) {}
    
    // ═══════════════════════════════════════════════════════════
    // لاگ کردن برای دیباگ
    // ═══════════════════════════════════════════════════════════
    console.log('✅ Stealth mode activated successfully');
    console.log('🤖 navigator.webdriver:', navigator.webdriver);
    console.log('🌐 window.chrome:', typeof window.chrome);
    console.log('🔌 navigator.plugins.length:', navigator.plugins.length);
})();
    """)

    logger.info("✅ Stealth context ساخته شد")

    return context


# ═══════════════════════════════════════════════════════════════
# تابع کمکی برای تست stealth
# ═══════════════════════════════════════════════════════════════
async def test_stealth_mode(page):
    """
    تست اینکه آیا stealth mode کار می‌کند

    استفاده:
        from browser.launcher import test_stealth_mode
        await test_stealth_mode(page)
    """
    logger.info("🧪 تست Stealth Mode...")

    # تست 1: navigator.webdriver
    webdriver = await page.evaluate("() => navigator.webdriver")
    logger.info(f"  🤖 navigator.webdriver: {webdriver}")

    if webdriver is None or webdriver is False or str(webdriver) == "undefined":
        logger.info("    ✅ PASS - webdriver مخفی شده")
    else:
        logger.warning("    ❌ FAIL - webdriver قابل شناسایی است!")

    # تست 2: window.chrome
    has_chrome = await page.evaluate("() => typeof window.chrome !== 'undefined'")
    logger.info(f"  🌐 window.chrome exists: {has_chrome}")

    if has_chrome:
        logger.info("    ✅ PASS - window.chrome موجود است")
    else:
        logger.warning("    ⚠️ WARN - window.chrome موجود نیست")

    # تست 3: navigator.plugins
    plugins_length = await page.evaluate("() => navigator.plugins.length")
    logger.info(f"  🔌 navigator.plugins.length: {plugins_length}")

    if plugins_length > 0:
        logger.info("    ✅ PASS - plugins موجود است")
    else:
        logger.warning("    ❌ FAIL - هیچ plugin موجود نیست!")

    # تست 4: canvas fingerprint
    canvas_test = await page.evaluate("""
        () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillText('Test', 2, 2);
            return canvas.toDataURL().substring(0, 50);
        }
    """)
    logger.info(f"  🎨 Canvas fingerprint: {canvas_test}")

    # تست 5: WebGL
    webgl_vendor = await page.evaluate("""
        () => {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl');
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            return gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        }
    """)
    logger.info(f"  🎮 WebGL vendor: {webgl_vendor}")

    logger.info("✅ تست Stealth Mode کامل شد")
