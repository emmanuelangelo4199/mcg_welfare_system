from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def role_required(allowed_roles=None):
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            # Allow superusers full access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check profile role
            user_profile = getattr(request.user, 'profile', None)
            if user_profile and user_profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, "You do not have permission to access this page.")
            return redirect('dashboard:dashboard')
        return _wrapped_view
    return decorator
