from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import SystemNotification

@login_required(login_url='accounts:login')
def notification_board_view(request):
    notifications = SystemNotification.objects.filter(user=request.user)
    return render(request, "notifications/notifi_board.html", {
        "active_nav": "notifications",
        "notifications": notifications
    })

@login_required(login_url='accounts:login')
def notification_settings_view(request):
    return render(request, "notifications/notifi_setting.html", {"active_nav": "notifications"})
