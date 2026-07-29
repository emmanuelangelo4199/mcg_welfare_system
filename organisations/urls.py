from django.urls import path
from . import views

app_name = 'organisations'

urlpatterns = [
    path('', views.org_list_view, name='org_list'),
    path('details/', views.org_details_view, name='org_details'),
    path('form/', views.add_edit_org_view, name='add_edit_org'),
    path('dues/', views.dues_contribution_view, name='dues_contribution'),
    path('attendance/', views.org_attendance_view, name='org_attendance'),
]
