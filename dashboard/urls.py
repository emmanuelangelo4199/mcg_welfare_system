from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.main_dashboard, name='dashboard'),
    path('treasurer/', views.treasurer_dashboard, name='treasurer_dashboard'),
    path('class-leader/', views.class_leader_dashboard, name='class_leader_dashboard'),
]