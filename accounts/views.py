from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from core.decorators import role_required
from core.models import AuditLog
from .models import UserProfile, Role, Module, RolePermission
from members.models import Member


User = get_user_model()

# ------------------------------------------------------------------
# Helpers to seed default data
# ------------------------------------------------------------------
DEFAULT_ROLES = [
    {"code": "ADMIN", "name": "Administrator", "description": "Global access to all system functions and configurations.", "is_system_protected": True},
    {"code": "SUPERINTENDENT_MINISTER", "name": "Superintendent Minister", "description": "Oversees circuit and society operations.", "is_system_protected": False},
    {"code": "SOCIETY_STEWARD", "name": "Society Steward", "description": "Manages society administration and stewardship.", "is_system_protected": False},
    {"code": "LEADERS_MEETING_SECRETARY", "name": "Leaders’ Meeting Secretary", "description": "Records minutes and manages governance docs.", "is_system_protected": False},
    {"code": "AUDITOR", "name": "Auditor", "description": "Reviews financial and operational records.", "is_system_protected": False},
    {"code": "TREASURER", "name": "Treasurer", "description": "Handles finance, budgets and reporting.", "is_system_protected": False},
    {"code": "CATECHIST", "name": "Catechist", "description": "Supports teaching and membership preparation.", "is_system_protected": False},
    {"code": "CIRCUIT_MINISTER", "name": "Circuit Minister", "description": "Circuit pastoral oversight.", "is_system_protected": False},
    {"code": "BIBLE_STUDY_LEADER", "name": "Bible Study Leaders", "description": "Leads bible study groups.", "is_system_protected": False},
    {"code": "CLASS_LEADER", "name": "Class Leaders", "description": "Manages class groups and attendance.", "is_system_protected": False},
    {"code": "ORGANISATION_LEADER", "name": "Organisation Leaders", "description": "Leads church organisations and groups.", "is_system_protected": False},
    {"code": "FINANCIAL_SECRETARY", "name": "Financial Secretary", "description": "Assists treasurer with records.", "is_system_protected": False},
    {"code": "SOCIETY_MINISTER", "name": "Society Minister", "description": "Society pastoral care.", "is_system_protected": False},
    {"code": "WELFARE_OFFICER", "name": "Welfare Officer", "description": "Manages welfare cases and support.", "is_system_protected": False},
    {"code": "MEMBER", "name": "Society Member", "description": "General member with limited access.", "is_system_protected": False},
]

DEFAULT_MODULES = [
    {"code": "MEMBERS", "name": "Members", "description": "Profiles and directory management", "order": 1, "is_sensitive": False},
    {"code": "CLASSES", "name": "Classes", "description": "Class groups and membership", "order": 2, "is_sensitive": False},
    {"code": "ORGANISATIONS", "name": "Organisations", "description": "Church organisations and groups", "order": 3, "is_sensitive": False},
    {"code": "SERVICES", "name": "Services", "description": "Service programs and events", "order": 4, "is_sensitive": False},
    {"code": "ATTENDANCE", "name": "Attendance", "description": "Service and class attendance", "order": 5, "is_sensitive": False},
    {"code": "FINANCE", "name": "Finance", "description": "Offerings, Tithes and Budgets", "order": 6, "is_sensitive": False},
    {"code": "WELFARE", "name": "Welfare", "description": "Sensitive support cases", "order": 7, "is_sensitive": True},
    {"code": "MEETINGS", "name": "Governance", "description": "Minutes, Agendas and Decisions", "order": 8, "is_sensitive": False},
    {"code": "COMMUNICATIONS", "name": "Communications", "description": "Messages and announcements", "order": 9, "is_sensitive": False},
    {"code": "REPORTS", "name": "Reports", "description": "Analytical and periodic statements", "order": 10, "is_sensitive": False},
    {"code": "SETTINGS", "name": "Settings", "description": "System-wide configurations", "order": 11, "is_sensitive": False},
]


def ensure_default_roles_and_modules():
    """Idempotent seeder for roles, modules and permissions."""
    for role_data in DEFAULT_ROLES:
        Role.objects.get_or_create(
            code=role_data["code"],
            defaults={
                "name": role_data["name"],
                "description": role_data["description"],
                "is_system_protected": role_data["is_system_protected"],
            },
        )

    for mod_data in DEFAULT_MODULES:
        Module.objects.get_or_create(
            code=mod_data["code"],
            defaults={
                "name": mod_data["name"],
                "description": mod_data["description"],
                "order": mod_data["order"],
                "is_sensitive": mod_data["is_sensitive"],
            },
        )

    # Ensure every role has a permission row per module
    roles = Role.objects.all()
    modules = Module.objects.all()
    for role in roles:
        for module in modules:
            perm, created = RolePermission.objects.get_or_create(
                role=role,
                module=module,
                defaults={
                    "can_view": True if role.code == "ADMIN" else False,
                    "can_create": True if role.code == "ADMIN" else False,
                    "can_edit": True if role.code == "ADMIN" else False,
                    "can_delete": True if role.code == "ADMIN" else False,
                    "can_approve": True if role.code == "ADMIN" else False,
                },
            )
            # For demo: give some sensible defaults for non-admin roles
            if created and role.code != "ADMIN":
                if role.code in ["TREASURER", "FINANCIAL_SECRETARY", "AUDITOR"] and module.code in ["FINANCE", "REPORTS"]:
                    perm.can_view = True
                    perm.can_create = role.code != "AUDITOR"
                    perm.can_edit = role.code != "AUDITOR"
                    perm.save()
                elif role.code in ["CLASS_LEADER"] and module.code in ["MEMBERS", "CLASSES", "ATTENDANCE"]:
                    perm.can_view = True
                    perm.can_edit = True
                    perm.save()
                elif role.code in ["WELFARE_OFFICER"] and module.code in ["WELFARE", "MEMBERS"]:
                    perm.can_view = True
                    perm.can_create = True
                    perm.can_edit = True
                    perm.save()


# ------------------------------------------------------------------
# Auth views (unchanged)
# --------------------------------
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
    if request.method == 'POST':
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('accounts:login')
    # GET requests are not accepted — redirect to dashboard or login
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    return redirect('accounts:login')

def password_reset_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        messages.info(request, f"If an account exists for {email}, password reset instructions have been sent.")
        return render(request, "accounts/a2.html", {"message_sent": True})
    return render(request, "accounts/a3.html")

@login_required(login_url='accounts:login')
def profile_view(request):
    """Display and update the currently authenticated account."""
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    member = Member.objects.filter(user=request.user).first()

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "info":
            email = request.POST.get("email", "").strip()
            phone = request.POST.get("phone", "").strip()
            has_error = False

            if email and email != request.user.email:
                if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                    messages.error(request, "That email address is already in use.")
                    has_error = True
                else:
                    request.user.email = email
                    request.user.save(update_fields=["email"])

            if not has_error:
                user_profile.phone_number = phone
                user_profile.save(update_fields=["phone_number"])

                AuditLog.objects.create(
                    user=request.user,
                    action="Updated profile information",
                    model_name="UserProfile",
                    object_id=str(user_profile.pk),
                    details=f"Email: {email}, Phone: {phone}",
                )
                messages.success(request, "Profile information saved successfully.")

            return redirect("accounts:profile")

        elif action == "password":
            current_password = request.POST.get("current_password", "")
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect("accounts:profile")

            if new_password != confirm_password:
                messages.error(request, "New password and confirmation do not match.")
                return redirect("accounts:profile")

            if len(new_password) < 8:
                messages.error(request, "New password must be at least 8 characters long.")
                return redirect("accounts:profile")

            if not any(c.isupper() for c in new_password):
                messages.error(request, "New password must contain at least one uppercase letter.")
                return redirect("accounts:profile")

            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for c in new_password):
                messages.error(request, "New password must contain at least one special character (!@#$ etc).")
                return redirect("accounts:profile")

            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)

            AuditLog.objects.create(
                user=request.user,
                action="Changed password",
                model_name="User",
                object_id=str(request.user.pk),
                details="Password updated via My Profile page",
            )

            messages.success(request, "Password updated successfully.")
            return redirect("accounts:profile")

    last_audited_log = AuditLog.objects.filter(user=request.user).order_by("-timestamp").first()
    last_audited_date = last_audited_log.timestamp if last_audited_log else None

    context = {
        "active_nav": "accounts",
        "profile": user_profile,
        "member": member,
        "last_audited": last_audited_date,
    }
    return render(request, "accounts/my_profile.html", context)


@role_required(allowed_roles=['ADMIN'])
def user_list_view(request):
    ensure_default_roles_and_modules()

    roles = Role.objects.filter(is_active=True).order_by('name')
    if not roles.exists():
        ensure_default_roles_and_modules()
        roles = Role.objects.filter(is_active=True).order_by('name')

    # Base queryset
    users_qs = User.objects.select_related('profile').all().order_by('-date_joined')

    # Filters from GET
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role_filter', '').strip()
    status_filter = request.GET.get('status', '').strip()  # active, inactive, all
    active_only = request.GET.get('active_only', '')

    if q:
        users_qs = users_qs.filter(
            models.Q(username__icontains=q)
            | models.Q(email__icontains=q)
            | models.Q(first_name__icontains=q)
            | models.Q(last_name__icontains=q)
            | models.Q(profile__phone_number__icontains=q)
        )

    if role_filter:
        users_qs = users_qs.filter(profile__role=role_filter)

    if status_filter == 'active' or active_only == 'on':
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        users_qs = users_qs.filter(is_active=False)

    # Stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users
    filtered_count = users_qs.count()

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(users_qs, 10)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)

    # For member linking in add user modal
    members = Member.objects.filter(user__isnull=True).order_by('first_name', 'last_name')[:100]

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action == 'update_role' or (request.POST.get('user_id') and request.POST.get('role') and not action):
            user_id = request.POST.get('user_id')
            new_role = request.POST.get('role')
            if user_id and new_role:
                target_user = get_object_or_404(User, id=user_id)
                profile, _ = UserProfile.objects.get_or_create(user=target_user)
                old_role = profile.role
                profile.role = new_role
                profile.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Changed user role from {old_role} to {new_role}",
                    model_name="UserProfile",
                    object_id=str(profile.pk),
                    details=f"User: {target_user.username}, New role: {new_role}",
                )

                messages.success(request, f"Updated role for '{target_user.username}' to {profile.get_role_display()}.")
                return redirect(f"{request.path}?{request.META.get('QUERY_STRING', '')}" if request.META.get('QUERY_STRING') else 'accounts:user_list')

        elif action == 'create_user':
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip()
            role_code = request.POST.get('role', '').strip()
            phone = request.POST.get('phone', '').strip()
            member_id = request.POST.get('member_id', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            setup = request.POST.get('setup', 'invitation')
            temp_password = request.POST.get('temp_password', '').strip()

            if not email:
                messages.error(request, "Email address is required.")
                return redirect('accounts:user_list')

            if User.objects.filter(email=email).exists():
                messages.error(request, f"A user with email {email} already exists.")
                return redirect('accounts:user_list')

            if not role_code:
                messages.error(request, "Role is required.")
                return redirect('accounts:user_list')

            # Split full name
            parts = full_name.split()
            first_name = parts[0] if parts else ''
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Password handling
            if setup == 'temp' and temp_password:
                password = temp_password
            else:
                # Generate random password or invitation flow
                import secrets, string
                alphabet = string.ascii_letters + string.digits + "!@#$"
                password = ''.join(secrets.choice(alphabet) for _ in range(12))
                if setup == 'temp' and not temp_password:
                    temp_password = password

            with transaction.atomic():
                new_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=is_active,
                )

                UserProfile.objects.create(
                    user=new_user,
                    role=role_code,
                    phone_number=phone,
                )

                # Link member if provided
                if member_id:
                    try:
                        member_obj = Member.objects.get(id=member_id)
                        member_obj.user = new_user
                        member_obj.save(update_fields=['user'])
                    except Member.DoesNotExist:
                        pass

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Created new user {new_user.username}",
                    model_name="User",
                    object_id=str(new_user.pk),
                    details=f"Email: {email}, Role: {role_code}, Active: {is_active}",
                )

            if setup == 'invitation':
                messages.success(request, f"User {email} created. Invitation link would be sent (demo). Temporary password: {password}")
            else:
                messages.success(request, f"User {email} created with temporary password: {temp_password or password}")

            return redirect('accounts:user_list')

        elif action == 'toggle_status':
            user_id = request.POST.get('user_id')
            if user_id:
                target_user = get_object_or_404(User, id=user_id)
                if target_user == request.user:
                    messages.error(request, "You cannot deactivate your own account.")
                else:
                    target_user.is_active = not target_user.is_active
                    target_user.save(update_fields=['is_active'])
                    AuditLog.objects.create(
                        user=request.user,
                        action=f"{'Activated' if target_user.is_active else 'Deactivated'} user {target_user.username}",
                        model_name="User",
                        object_id=str(target_user.pk),
                    )
                    messages.success(request, f"User {target_user.username} {'activated' if target_user.is_active else 'deactivated'}.")
                return redirect('accounts:user_list')

        elif action == 'delete_user':
            user_id = request.POST.get('user_id')
            if user_id:
                target_user = get_object_or_404(User, id=user_id)
                if target_user == request.user:
                    messages.error(request, "You cannot delete your own account.")
                elif target_user.is_superuser:
                    messages.error(request, "Cannot delete superuser.")
                else:
                    username = target_user.username
                    target_user.delete()
                    AuditLog.objects.create(
                        user=request.user,
                        action=f"Deleted user {username}",
                        model_name="User",
                        object_id=str(user_id),
                    )
                    messages.success(request, f"User {username} deleted.")
                return redirect('accounts:user_list')

    context = {
        "active_nav": "accounts",
        "users": users_page,
        "users_page": users_page,
        "roles": roles,
        "role_choices": UserProfile.ROLE_CHOICES,
        "members": members,
        "q": q,
        "role_filter": role_filter,
        "status_filter": status_filter,
        "active_only": active_only,
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "filtered_count": filtered_count,
        "paginator": paginator,
    }
    return render(request, "accounts/user_management.html", context)

@role_required(allowed_roles=['ADMIN'])
def roles_permissions_view(request):
    """
    Dynamic Role & Permission Management:
    - Lists all roles (left panel)
    - Shows permission matrix for selected role (right panel)
    - Allows saving permissions
    """
    ensure_default_roles_and_modules()

    # Determine selected role
    selected_code = request.GET.get('role', 'ADMIN')
    selected_role = Role.objects.filter(code=selected_code, is_active=True).first()
    if not selected_role:
        selected_role = Role.objects.filter(code='ADMIN').first()
        if not selected_role:
            selected_role = Role.objects.filter(is_active=True).first()

    roles = Role.objects.filter(is_active=True).order_by('name')
    modules = Module.objects.all().order_by('order', 'name')

    # Ensure permissions exist for selected role
    for module in modules:
        RolePermission.objects.get_or_create(role=selected_role, module=module)

    permissions_qs = RolePermission.objects.filter(role=selected_role).select_related('module')
    permissions_map = {p.module.code: p for p in permissions_qs}

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action == 'save_permissions':
            role_code = request.POST.get('role_code', '').strip()
            role_obj = get_object_or_404(Role, code=role_code)

            if role_obj.is_system_protected:
                messages.error(request, f"{role_obj.name} is system protected and cannot be modified.")
                return redirect(f"{request.path}?role={role_code}")

            updated_count = 0
            with transaction.atomic():
                for module in modules:
                    perm = RolePermission.objects.get(role=role_obj, module=module)
                    # Checkbox values: if checked, key exists in POST
                    perm.can_view = f"perm_{module.code}_view" in request.POST
                    perm.can_create = f"perm_{module.code}_create" in request.POST
                    perm.can_edit = f"perm_{module.code}_edit" in request.POST
                    perm.can_delete = f"perm_{module.code}_delete" in request.POST
                    perm.can_approve = f"perm_{module.code}_approve" in request.POST
                    perm.save()
                    updated_count += 1

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Updated permissions for role {role_obj.name}",
                    model_name="RolePermission",
                    object_id=str(role_obj.pk),
                    details=f"Updated {updated_count} module permissions for role {role_code}",
                )

            messages.success(request, f"Permissions for {role_obj.name} saved successfully.")
            return redirect(f"{request.path}?role={role_code}")

        elif action == 'create_role':
            code = request.POST.get('code', '').strip().upper().replace(' ', '_')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()

            if not code or not name:
                messages.error(request, "Role code and name are required.")
                return redirect(f"{request.path}?role={selected_role.code}")

            if Role.objects.filter(code=code).exists():
                messages.error(request, f"Role with code {code} already exists.")
                return redirect(f"{request.path}?role={code}")

            role = Role.objects.create(
                code=code,
                name=name,
                description=description,
                is_system_protected=False,
            )

            # Create permissions for all modules
            for module in modules:
                RolePermission.objects.create(role=role, module=module)

            AuditLog.objects.create(
                user=request.user,
                action=f"Created new role {name}",
                model_name="Role",
                object_id=str(role.pk),
                details=f"Code: {code}, Name: {name}",
            )

            messages.success(request, f"Role {name} created successfully.")
            return redirect(f"{request.path}?role={code}")

        # Legacy: user role assignment (kept for backwards compatibility)
        elif action == 'assign_user_role' or request.POST.get('user_id'):
            user_id = request.POST.get('user_id')
            new_role = request.POST.get('role')
            if user_id and new_role:
                target_user = get_object_or_404(User, id=user_id)
                profile, _ = UserProfile.objects.get_or_create(user=target_user)
                old_role = profile.role
                profile.role = new_role
                profile.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Changed user role from {old_role} to {new_role} via role management",
                    model_name="UserProfile",
                    object_id=str(profile.pk),
                    details=f"User: {target_user.username}",
                )

                messages.success(request, f"Role for '{target_user.username}' updated to {profile.get_role_display()}.")
                return redirect(f"{request.path}?role={new_role}")

    # For sidebar: count users per role
    role_user_counts = {
        up['role']: up['count']
        for up in UserProfile.objects.values('role').annotate(count=models.Count('role'))
    }

    # Recent audit logs for this feature
    recent_logs = AuditLog.objects.filter(model_name__in=['Role', 'RolePermission', 'UserProfile']).order_by('-timestamp')[:10]

    context = {
        "active_nav": "accounts",
        "roles": roles,
        "selected_role": selected_role,
        "modules": modules,
        "permissions_map": permissions_map,
        "role_user_counts": role_user_counts,
        "recent_logs": recent_logs,
        "role_choices": UserProfile.ROLE_CHOICES,
    }
    return render(request, "accounts/role_management.html", context)