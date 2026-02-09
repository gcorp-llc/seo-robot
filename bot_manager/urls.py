from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('start/<int:site_id>/', views.start_bot, name='start_bot'),
    path('job-status/<int:job_id>/', views.job_status, name='job_status'),
    path('proxy-sync/', views.proxy_sync, name='proxy_sync'),
]
