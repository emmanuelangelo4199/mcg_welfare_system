from django.shortcuts import render

def system_settings_view(request):
    return render(request, "core/system_setting.html")

def audit_log_view(request):
    return render(request, "core/audit_log.html")
