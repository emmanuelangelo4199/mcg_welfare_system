from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.member_directory_view, name='member_directory'),
    path('register/', views.member_registration_view, name='member_registration'),
    path('profile/', views.member_profile_view, name='member_profile'),
    path('edit/', views.edit_member_view, name='edit_member'),
    path('pending/', views.pending_members_view, name='pending_members'),
    path('regularisation/', views.member_regularisation_view, name='member_regularisation'),
    path('transfer/', views.member_transfer_view, name='member_transfer'),
    path('status/', views.status_management_view, name='status_management'),
]
