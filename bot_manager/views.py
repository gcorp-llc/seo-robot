from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import SiteConfig, BotJob, Proxy, SearchEngine
from django_q.tasks import async_task

def dashboard(request):
    sites = SiteConfig.objects.all()
    jobs = BotJob.objects.order_by('-started_at')[:10]
    proxies_count = Proxy.objects.count()
    active_proxies = Proxy.objects.filter(is_active=True).count()
    engines = SearchEngine.objects.all()

    return render(request, 'bot_manager/dashboard.html', {
        'sites': sites,
        'jobs': jobs,
        'proxies_count': proxies_count,
        'active_proxies': active_proxies,
        'engines': engines,
    })

def start_bot(request, site_id):
    site = get_object_or_404(SiteConfig, pk=site_id)
    job = BotJob.objects.create(site=site, status='pending', current_step='در انتظار شروع...')

    # اینجا تسک async را صدا می‌زنیم
    async_task('bot_manager.tasks.run_bot_task', site.id, job.id)

    return redirect('dashboard')

def job_status(request, job_id):
    job = get_object_or_404(BotJob, pk=job_id)
    return JsonResponse({
        'status': job.get_status_display(),
        'progress': job.progress,
        'current_step': job.current_step,
        'finished': job.status in ['completed', 'failed']
    })

def proxy_sync(request):
    from .models import ProxySource
    source = ProxySource.objects.first()
    if not source:
        return JsonResponse({'status': 'error', 'message': 'هیچ منبع پروکسی تعریف نشده است.'})

    async_task('bot_manager.tasks.sync_proxies_task', source.id)
    return JsonResponse({'status': 'success', 'message': 'عملیات همگام‌سازی پروکسی‌ها شروع شد.'})
