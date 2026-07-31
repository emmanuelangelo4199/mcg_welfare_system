from django.urls import path
from . import views

app_name = 'accounts' 

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('profile/', views.profile_view, name='profile'),
    path('roles/', views.user_list_view, name='roles_permissions'),
    path('users/', views.roles_permissions_view, name='user_list'),
]
