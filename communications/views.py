from django.shortcuts import render

def compose_message_view(request):
    return render(request, "communications/compose_msg.html", {"active_nav": "communications"})

def message_history_view(request):
    return render(request, "communications/k2msg_history.html", {"active_nav": "communications"})

def announcement_board_view(request):
    return render(request, "communications/k3ann_board.html", {"active_nav": "communications"})

def birthday_messages_view(request):
    return render(request, "communications/k4birthday_message.html", {"active_nav": "communications"})

def reminder_due_notice_view(request):
    return render(request, "communications/k5reminder_due_notice.html", {"active_nav": "communications"})
