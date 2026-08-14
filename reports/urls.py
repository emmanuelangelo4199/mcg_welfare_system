from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_hub_view, name='reports_hub'),
    path('membership/', views.membership_report_view, name='membership_report'),
    path('attendance/', views.attendance_report_view, name='attendance_report'),
    path('finance/', views.finance_report_view, name='finance_report'),
    path('welfare/', views.welfare_report_view, name='welfare_report'),
    path('annual/', views.annual_report_view, name='annual_report'),
    # Export CSVs
    path('export/members/', views.export_members_csv, name='export_members_csv'),
    path('export/finance/', views.export_finance_csv, name='export_finance_csv'),
    path('export/welfare/', views.export_welfare_csv, name='export_welfare_csv'),
]
