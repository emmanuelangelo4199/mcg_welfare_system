from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [ 
    path('', views.upcoming_events_view, name='upcoming_events'),
    path('calendar/', views.event_calendar_view, name='event_calendar'),
    path('program-form/', views.service_program_form_view, name='service_program_form'),
    path('detail/', views.service_detail_view, name='service_detail'),
    path('attendance/', views.service_attendance_view, name='service_attendance'),
]
