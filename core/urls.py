from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('settings/', views.system_settings_view, name='system_settings'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
]
