"""نمای‌های پنل مدیریت ربات SEO

بهبودهای اعمال‌شده نسبت به نسخه قبل:
- تبدیل به نمای‌های کلاس‌محور (CBV) با QuerySetهای بهینه (select_related / annotate).
- حذف کوئری‌های تکراری N+1 در داشبورد (یک aggregation به‌جای چند count).
- محافظت از شروع عملیات در برابر دوبار کلیک (جلوگیری از صف شدن چند Job همزمان برای یک سایت).
- همه actionها POST + CSRF هستند و پیام‌های موفقیت/خطا با Messages نمایش داده می‌شود.
- صفحات جدید: لیست عملیات‌ها، جزئیات هر عملیات (لاگ زنده)، مدیریت پروکسی و منابع پروکسی.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.generic import DetailView, ListView, TemplateView, View

from django_q.tasks import async_task

from .models import BotJob, Device, Proxy, ProxySource, SearchEngine, SiteConfig


class DashboardView(LoginRequiredMixin, TemplateView):
    """داشبورد اصلی: آمار کلی، سایت‌های هدف و عملیات‌های اخیر."""

    template_name = "bot_manager/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # یک کوئری گروهی به‌جای چندین count جداگانه (بهبود کارایی)
        proxy_stats = Proxy.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
        )

        sites = (
            SiteConfig.objects
            .annotate(
                keywords_count=Count("keywords", distinct=True),
                links_count=Count("crawled_links", distinct=True),
                visited_count=Count("crawled_links", filter=Q(crawled_links__is_visited=True), distinct=True),
            )
            .prefetch_related("keywords")
        )

        recent_jobs = BotJob.objects.select_related("site")[:8]

        # وضعیت سیستم صف (Django-Q) - فقط در صورت موجود بودن جدول‌ها
        queue_info = {"workers": getattr(settings, "Q_CLUSTER", {}).get("workers", 4),
                      "queued": None, "success": None, "failed": None}
        try:
            from django_q.models import OrmQ, Success, Failure
            queue_info["queued"] = OrmQ.objects.count()
            last_24h = timezone.now() - timezone.timedelta(hours=24)
            queue_info["success"] = Success.objects.filter(create__gte=last_24h).count()
            queue_info["failed"] = Failure.objects.filter(create__gte=last_24h).count()
        except Exception:
            pass

        jobs_summary = BotJob.objects.aggregate(
            running_total=Count("id", filter=Q(status="running")),
            completed_total=Count("id", filter=Q(status="completed")),
            failed_total=Count("id", filter=Q(status="failed")),
        )

        ctx.update({
            "sites": sites,
            "jobs": recent_jobs,
            "proxies_count": proxy_stats["total"],
            "active_proxies": proxy_stats["active"],
            "engines": SearchEngine.objects.all(),
            "devices_count": Device.objects.filter(is_active=True).count(),
            "queue_info": queue_info,
            **jobs_summary,
            "now_ts": timezone.now().timestamp(),
        })
        return ctx


class StartBotView(LoginRequiredMixin, View):
    """شروع یک عملیات جدید برای سایت هدف (فقط POST)."""

    def post(self, request, site_id):
        site = get_object_or_404(SiteConfig, pk=site_id)

        # جلوگیری از اجرای همزمان چند عملیات برای یک سایت (بهبود UX و کارایی)
        if BotJob.objects.filter(site=site, status__in=["pending", "running"]).exists():
            messages.warning(request, f"عملیات «{site.name}» همین حالا در حال اجرا است.")
        else:
            job = BotJob.objects.create(site=site, status="pending", current_step="در انتظار شروع...")
            async_task("bot_manager.tasks.run_bot_task", site.id, job.id,
                       task_name=f"SEO Bot - {site.name}")
            messages.success(request, f"عملیات «{site.name}» در صف اجرای پس‌زمینه قرار گرفت.")

        return redirect(reverse_lazy("dashboard"))


@never_cache
def job_status(request, job_id):
    """وضعیت لحظه‌ای یک عملیات - برای Polling جاوااسکریپت."""
    job = get_object_or_404(BotJob, pk=job_id)
    return JsonResponse({
        "status": job.status,
        "status_display": job.get_status_display(),
        "progress": job.progress,
        "current_step": job.current_step,
        "duration": job.duration_seconds,
        "finished": job.status in ("completed", "failed"),
    })


class SyncProxiesView(LoginRequiredMixin, View):
    """همگام‌سازی پروکسی‌ها از همه منابع ثبت‌شده (فقط POST)."""

    def post(self, request):
        sources = list(ProxySource.objects.all())
        if not sources:
            messages.error(request, "هیچ منبع پروکسی تعریف نشده است. ابتدا از بخش «منابع پروکسی» یک منبع اضافه کنید.")
        else:
            for source in sources:
                async_task("bot_manager.tasks.sync_proxies_task", source.id,
                           task_name=f"Proxy Sync - {source.url[:40]}")
            messages.success(request, f"همگام‌سازی {len(sources)} منبع پروکسی در پس‌زمینه شروع شد.")
        return redirect(request.POST.get("next") or reverse_lazy("dashboard"))


class ToggleProxyView(LoginRequiredMixin, View):
    """فعال/غیرفعال کردن سریع یک پروکسی از لیست."""

    def post(self, request, proxy_id):
        proxy = get_object_or_404(Proxy, pk=proxy_id)
        proxy.is_active = not proxy.is_active
        proxy.save(update_fields=["is_active"])
        messages.success(request, f"پروکسی {proxy.url} {'فعال' if proxy.is_active else 'غیرفعال'} شد.")
        return redirect(reverse_lazy("proxy_list"))


class CheckProxiesView(LoginRequiredMixin, View):
    """بررسی سلامت پروکسی‌های فعال در پس‌زمینه."""

    def post(self, request):
        count = Proxy.objects.filter(is_active=True).count()
        if count == 0:
            messages.warning(request, "پروکسی فعالی برای بررسی وجود ندارد.")
        else:
            async_task("bot_manager.tasks.check_proxies_task", task_name="Proxy Health Check")
            messages.success(request, f"بررسی سلامت {count} پروکسی فعال در پس‌زمینه شروع شد.")
        return redirect(reverse_lazy("proxy_list"))


class JobListView(LoginRequiredMixin, ListView):
    """لیست کامل عملیات‌ها با صفحه‌بندی."""

    model = BotJob
    template_name = "bot_manager/job_list.html"
    context_object_name = "jobs"
    paginate_by = 20

    def get_queryset(self):
        qs = BotJob.objects.select_related("site").order_by("-started_at")
        status_filter = self.request.GET.get("status")
        if status_filter in ("pending", "running", "completed", "failed"):
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx


class JobDetailView(LoginRequiredMixin, DetailView):
    """جزئیات یک عملیات شامل لاگ کامل."""

    model = BotJob
    template_name = "bot_manager/job_detail.html"
    context_object_name = "job"

    def get_queryset(self):
        return BotJob.objects.select_related("site")


class ProxyListView(LoginRequiredMixin, ListView):
    """مدیریت پروکسی‌ها با فیلتر و صفحه‌بندی."""

    model = Proxy
    template_name = "bot_manager/proxy_list.html"
    context_object_name = "proxies"
    paginate_by = 50

    def get_queryset(self):
        qs = Proxy.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(url__icontains=q)
        state = self.request.GET.get("state", "")
        if state == "active":
            qs = qs.filter(is_active=True)
        elif state == "inactive":
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        stats = Proxy.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
        )
        ctx.update({
            "proxies_count": stats["total"],
            "active_proxies": stats["active"],
            "sources": ProxySource.objects.all(),
            "current_q": self.request.GET.get("q", ""),
            "current_state": self.request.GET.get("state", ""),
        })
        return ctx
