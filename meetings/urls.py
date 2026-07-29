from django.urls import path
from . import views

app_name = 'meetings'

urlpatterns = [
    path('', views.meeting_list_view, name='meeting_list'),
    path('schedule/', views.meeting_schedule_view, name='meeting_schedule'),
    path('details/', views.meeting_details_view, name='meeting_details'),
    path('minutes-editor/', views.meeting_minutes_editor_view, name='meeting_minutes_editor'),
    path('action-items/', views.action_item_tracker_view, name='action_item_tracker'),
]
