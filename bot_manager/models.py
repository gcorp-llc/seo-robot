from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class SiteConfig(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام سایت")
    main_url = models.URLField(verbose_name="آدرس اصلی سایت")
    articles_url = models.URLField(verbose_name="آدرس بخش مقالات")
    search_engines_enabled = models.BooleanField(default=True, verbose_name="جستجو در موتورهای جستجو فعال باشد؟")
    visits_per_run = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name="حداکثر مقاله در هر عملیات",
        help_text="تعداد مقالاتی که ربات در هر اجرا به‌صورت تصادفی مطالعه می‌کند (۱ تا ۲۰).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name

class Keyword(models.Model):
    site = models.ForeignKey(SiteConfig, related_name='keywords', on_delete=models.CASCADE)
    word = models.CharField(max_length=255, verbose_name="کلمه کلیدی")

    class Meta:
        verbose_name = "کلمه کلیدی"
        verbose_name_plural = "کلمات کلیدی"
        ordering = ["word"]
        constraints = [
            models.UniqueConstraint(fields=["site", "word"], name="unique_keyword_per_site"),
        ]

    def __str__(self):
        return self.word


class SearchEngine(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام موتور جستجو")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "موتور جستجو"
        verbose_name_plural = "موتورهای جستجو"
        ordering = ["name"]

    def __str__(self):
        return self.name

class ProxySource(models.Model):
    url = models.URLField(max_length=500, verbose_name="لینک دریافت لیست پروکسی")
    last_sync = models.DateTimeField(auto_now=True, verbose_name="آخرین همگام‌سازی")

    class Meta:
        verbose_name = "منبع پروکسی"
        verbose_name_plural = "منابع پروکسی"
        ordering = ["url"]

    def __str__(self):
        return self.url


class Proxy(models.Model):
    url = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="URL پروکسی (e.g. http://user:pass@ip:port)",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    last_checked = models.DateTimeField(null=True, blank=True, verbose_name="آخرین بررسی")
    status_code = models.IntegerField(null=True, blank=True, verbose_name="کد وضعیت")
    latency_ms = models.IntegerField(null=True, blank=True, verbose_name="تاخیر (میلی‌ثانیه)")

    class Meta:
        verbose_name = "پروکسی"
        verbose_name_plural = "پروکسی‌ها"
        ordering = ["-is_active", "url"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return self.url


class Device(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="نام دستگاه")
    config_json = models.JSONField(verbose_name="تنظیمات دستگاه (JSON)")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "دستگاه"
        verbose_name_plural = "دستگاه‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BotJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('running', 'در حال اجرا'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
    ]
    site = models.ForeignKey(SiteConfig, on_delete=models.CASCADE, verbose_name="سایت")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    progress = models.IntegerField(default=0, verbose_name="پیشرفت")
    current_step = models.CharField(max_length=255, blank=True, verbose_name="مرحله فعلی")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان شروع")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پایان")
    log = models.TextField(blank=True, verbose_name="لاگ")

    class Meta:
        verbose_name = "عملیات ربات"
        verbose_name_plural = "عملیات‌های ربات"
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["status", "-started_at"])]

    def __str__(self):
        return f"عملیات {self.site.name} ({self.get_status_display()})"

    @property
    def duration_seconds(self):
        """مدت زمان اجرای عملیات (برای عملیات در حال اجرا، زمان جاری مبنا است)."""
        if not self.started_at:
            return None
        from django.utils import timezone
        end = self.finished_at or timezone.now()
        return int((end - self.started_at).total_seconds())


class CrawledLink(models.Model):
    site = models.ForeignKey(SiteConfig, related_name='crawled_links', on_delete=models.CASCADE)
    url = models.URLField(max_length=500, verbose_name="آدرس")
    is_visited = models.BooleanField(default=False, verbose_name="بازدید شده")
    discovered_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان کشف")

    class Meta:
        verbose_name = "لینک کرال شده"
        verbose_name_plural = "لینک‌های کرال شده"
        ordering = ["-discovered_at"]
        constraints = [
            models.UniqueConstraint(fields=["site", "url"], name="unique_crawled_link_per_site"),
        ]

    def __str__(self):
        return self.url
