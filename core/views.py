from django.shortcuts import render, redirect
from django.contrib import messages
from core.decorators import role_required
from .models import SystemSetting, AuditLog

@role_required(allowed_roles=['ADMIN'])
def system_settings_view(request):
    if request.method == 'POST':
        key = request.POST.get('key', '').strip()
        value = request.POST.get('value', '').strip()
        desc = request.POST.get('description', '').strip()

        if key:
            SystemSetting.objects.update_or_create(
                key=key,
                defaults={'value': value, 'description': desc}
            )
            messages.success(request, f"Setting '{key}' updated successfully.")
            return redirect('core:system_settings')

    settings = SystemSetting.objects.all()
    return render(request, "core/system_setting.html", {
        "active_nav": "core",
        "settings": settings
    })

@role_required(allowed_roles=['ADMIN'])
def audit_log_view(request):
    logs = AuditLog.objects.select_related('user').all()[:100]
    return render(request, "core/audit_log.html", {
        "active_nav": "core",
        "logs": logs
    })
