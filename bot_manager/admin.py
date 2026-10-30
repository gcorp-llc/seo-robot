from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import SiteConfig, Keyword, SearchEngine, Proxy, Device, BotJob, ProxySource, CrawledLink


class KeywordInline(admin.TabularInline):
    model = Keyword
    extra = 1


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'main_url', 'search_engines_enabled', 'visits_per_run', 'keywords_count')
    list_filter = ('search_engines_enabled',)
    search_fields = ('name', 'main_url')
    inlines = [KeywordInline]

    @admin.display(description="تعداد کلمات کلیدی")
    def keywords_count(self, obj):
        return obj.keywords.count()


@admin.register(SearchEngine)
class SearchEngineAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)
    ordering = ('name',)


@admin.register(ProxySource)
class ProxySourceAdmin(admin.ModelAdmin):
    list_display = ('url', 'last_sync')
    readonly_fields = ('last_sync',)


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ('url', 'is_active', 'latency_ms', 'status_code', 'last_checked')
    list_filter = ('is_active',)
    search_fields = ('url',)
    readonly_fields = ('last_checked', 'status_code', 'latency_ms')

    def get_queryset(self, request):
        # صفحه‌بندی برای لیست‌های بزرگ پروکسی (بهبود کارایی admin)
        return super().get_queryset(request).order_by('-is_active', 'url')


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name',)


@admin.register(BotJob)
class BotJobAdmin(admin.ModelAdmin):
    list_display = ('site', 'status_badge', 'progress', 'started_at', 'finished_at', 'view_in_panel')
    list_filter = ('status', 'site')
    readonly_fields = ('started_at', 'finished_at', 'log', 'progress', 'current_step')
    autocomplete_fields = ('site',)

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        colors = {'completed': '#16a34a', 'failed': '#dc2626', 'running': '#2563eb', 'pending': '#6b7280'}
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            colors.get(obj.status, '#000'), obj.get_status_display(),
        )

    @admin.display(description="پنل مدیریت")
    def view_in_panel(self, obj):
        url = reverse('job_detail', args=[obj.pk])
        return format_html('<a href="{}">مشاهده لاگ زنده ↗</a>', url)


@admin.register(CrawledLink)
class CrawledLinkAdmin(admin.ModelAdmin):
    list_display = ('url', 'site', 'is_visited', 'discovered_at')
    list_filter = ('is_visited', 'site')
    search_fields = ('url',)
    list_select_related = ('site',)

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-discovered_at')[:5000]
