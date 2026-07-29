from django.urls import path
from . import views

app_name = 'classes'

urlpatterns = [
    path('', views.class_list_view, name='class_list'),
    path('detail/', views.class_detail_view, name='class_detail'),
    path('form/', views.add_edit_class_view, name='add_edit_class'),
    path('attendance-record/', views.class_attendance_record_view, name='class_attendance_record'),
    path('attendance-report/', views.class_attendance_report_view, name='class_attendance_report'),
]
