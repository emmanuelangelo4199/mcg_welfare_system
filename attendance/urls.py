from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.overview_view, name='overview'),
    path('service/', views.service_attendance_view, name='service_attendance'),
    path('class/', views.class_attendance_view, name='class_attendance'),
    path('organisation/', views.org_attendance_view, name='org_attendance'),
    path('absentee-report/', views.absentee_report_view, name='absentee_report'),
]
