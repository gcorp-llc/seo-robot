from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("start/<int:site_id>/", views.StartBotView.as_view(), name="start_bot"),
    path("job-status/<int:job_id>/", views.job_status, name="job_status"),
    path("jobs/", views.JobListView.as_view(), name="job_list"),
    path("jobs/<int:pk>/", views.JobDetailView.as_view(), name="job_detail"),
    path("proxies/", views.ProxyListView.as_view(), name="proxy_list"),
    path("proxies/sync/", views.SyncProxiesView.as_view(), name="proxy_sync"),
    path("proxies/check/", views.CheckProxiesView.as_view(), name="proxy_check"),
    path("proxies/toggle/<int:proxy_id>/", views.ToggleProxyView.as_view(), name="proxy_toggle"),
]
