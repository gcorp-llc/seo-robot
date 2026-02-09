from django.contrib import admin
from .models import SiteConfig, Keyword, SearchEngine, Proxy, Device, BotJob, ProxySource, CrawledLink

class KeywordInline(admin.TabularInline):
    model = Keyword
    extra = 1

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'main_url', 'search_engines_enabled')
    inlines = [KeywordInline]

@admin.register(SearchEngine)
class SearchEngineAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)

@admin.register(ProxySource)
class ProxySourceAdmin(admin.ModelAdmin):
    list_display = ('url', 'last_sync')

@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ('url', 'is_active', 'last_checked', 'status_code')
    list_filter = ('is_active', 'status_code')

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)

@admin.register(BotJob)
class BotJobAdmin(admin.ModelAdmin):
    list_display = ('site', 'status', 'progress', 'started_at', 'finished_at')
    readonly_fields = ('started_at', 'finished_at', 'log')

@admin.register(CrawledLink)
class CrawledLinkAdmin(admin.ModelAdmin):
    list_display = ('url', 'site', 'is_visited', 'discovered_at')
    list_filter = ('is_visited', 'site')
    search_fields = ('url',)
