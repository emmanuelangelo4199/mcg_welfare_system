from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_board_view, name='notification_board'),
    path('settings/', views.notification_settings_view, name='notification_settings'),
    path('mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('clear-all/', views.notification_clear_all, name='notification_clear_all'),
    path('<int:pk>/toggle-read/', views.notification_toggle_read, name='notification_toggle_read'),
    path('<int:pk>/delete/', views.notification_delete, name='notification_delete'),
]
