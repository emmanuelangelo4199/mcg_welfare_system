from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.decorators import role_required
from .models import UserProfile

User = get_user_model()

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        email_or_username = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        user = None
        if '@' in email_or_username:
            try:
                user_obj = User.objects.get(email=email_or_username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=email_or_username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            return redirect(next_url or 'dashboard:dashboard')
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, "accounts/a1.html")

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not username:
            username = email.split('@')[0] if email else 'user'

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
        elif email and User.objects.filter(email=email).exists():
            messages.error(request, "Email address is already registered.")
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            UserProfile.objects.create(
                user=user,
                phone_number=phone,
                role='MEMBER'
            )
            messages.success(request, "Account created successfully! Please sign in.")
            return redirect('accounts:login')

    return render(request, "accounts/a2.html")

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')

def password_reset_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        messages.info(request, f"If an account exists for {email}, password reset instructions have been sent.")
        return render(request, "accounts/a2.html", {"message_sent": True})
    return render(request, "accounts/a3.html")

@login_required(login_url='accounts:login')
def profile_view(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, "accounts/my_profile.html", {
        "active_nav": "accounts",
        "profile": user_profile
    })

@role_required(allowed_roles=['ADMIN'])
def user_list_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        if user_id and new_role:
            target_user = get_object_or_404(User, id=user_id)
            profile, _ = UserProfile.objects.get_or_create(user=target_user)
            profile.role = new_role
            profile.save()
            messages.success(request, f"Updated role for '{target_user.username}' to {profile.get_role_display()}.")
            return redirect('accounts:user_list')

    users = User.objects.select_related('profile').all()
    return render(request, "accounts/user_management.html", {
        "active_nav": "accounts",
        "users": users
    })

@role_required(allowed_roles=['ADMIN'])
def roles_permissions_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        if user_id and new_role:
            target_user = get_object_or_404(User, id=user_id)
            profile, _ = UserProfile.objects.get_or_create(user=target_user)
            profile.role = new_role
            profile.save()
            messages.success(request, f"Role for '{target_user.username}' updated to {profile.get_role_display()}.")
            return redirect('accounts:roles_permissions')

    users = User.objects.select_related('profile').all()
    return render(request, "accounts/role_management.html", {
        "active_nav": "accounts",
        "users": users
    })
