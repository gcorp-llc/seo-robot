from django.db import models

class SiteConfig(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام سایت")
    main_url = models.URLField(verbose_name="آدرس اصلی سایت")
    articles_url = models.URLField(verbose_name="آدرس بخش مقالات")
    search_engines_enabled = models.BooleanField(default=True, verbose_name="جستجو در موتورهای جستجو فعال باشد؟")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت‌ها"

    def __str__(self):
        return self.name

class Keyword(models.Model):
    site = models.ForeignKey(SiteConfig, related_name='keywords', on_delete=models.CASCADE)
    word = models.CharField(max_length=255, verbose_name="کلمه کلیدی")

    class Meta:
        verbose_name = "کلمه کلیدی"
        verbose_name_plural = "کلمات کلیدی"

    def __str__(self):
        return self.word

class SearchEngine(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام موتور جستجو")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "موتور جستجو"
        verbose_name_plural = "موتورهای جستجو"

    def __str__(self):
        return self.name

class ProxySource(models.Model):
    url = models.URLField(verbose_name="لینک دریافت لیست پروکسی")
    last_sync = models.DateTimeField(auto_now=True, verbose_name="آخرین همگام‌سازی")

    class Meta:
        verbose_name = "منبع پروکسی"
        verbose_name_plural = "منابع پروکسی"

    def __str__(self):
        return self.url

class Proxy(models.Model):
    url = models.CharField(max_length=255, verbose_name="URL پروکسی (e.g. http://user:pass@ip:port)")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    last_checked = models.DateTimeField(auto_now=True, verbose_name="آخرین بررسی")
    status_code = models.IntegerField(null=True, blank=True, verbose_name="کد وضعیت")

    class Meta:
        verbose_name = "پروکسی"
        verbose_name_plural = "پروکسی‌ها"

    def __str__(self):
        return self.url

class Device(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام دستگاه")
    config_json = models.JSONField(verbose_name="تنظیمات دستگاه (JSON)")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "دستگاه"
        verbose_name_plural = "دستگاه‌ها"

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

    def __str__(self):
        return f"Job for {self.site.name} at {self.started_at}"

class CrawledLink(models.Model):
    site = models.ForeignKey(SiteConfig, related_name='crawled_links', on_delete=models.CASCADE)
    url = models.URLField(max_length=500, verbose_name="آدرس")
    is_visited = models.BooleanField(default=False, verbose_name="بازدید شده")
    discovered_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان کشف")

    class Meta:
        verbose_name = "لینک کرال شده"
        verbose_name_plural = "لینک‌های کرال شده"

    def __str__(self):
        return self.url
