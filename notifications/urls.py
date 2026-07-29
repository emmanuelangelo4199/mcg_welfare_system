from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_board_view, name='notification_board'),
    path('settings/', views.notification_settings_view, name='notification_settings'),
]
