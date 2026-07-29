from django.shortcuts import render

def notification_board_view(request):
    return render(request, "notifications/notifi_board.html")

def notification_settings_view(request):
    return render(request, "notifications/notifi_setting.html")
