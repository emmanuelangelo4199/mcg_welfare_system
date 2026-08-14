from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Announcement, OutgoingMessage
from members.models import Member
import datetime

@login_required(login_url='accounts:login')
def compose_message_view(request):
    if request.method == 'POST':
        msg_type = request.POST.get('type', 'SMS')
        group = request.POST.get('recipient_group', 'All Members')
        subject = request.POST.get('subject', '').strip()
        content = request.POST.get('content', '').strip()

        OutgoingMessage.objects.create(
            recipient_group=group,
            message_type=msg_type,
            subject=subject,
            content=content
        )
        messages.success(request, f"{msg_type} message sent to {group}.")
        return redirect('communications:message_history')

    return render(request, "communications/compose_msg.html", {"active_nav": "communications"})

@login_required(login_url='accounts:login')
def message_history_view(request):
    messages_list = OutgoingMessage.objects.all().order_by('-sent_at')
    return render(request, "communications/k2msg_history.html", {
        "active_nav": "communications",
        "messages_list": messages_list
    })

@login_required(login_url='accounts:login')
def announcement_board_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        Announcement.objects.create(
            title=title,
            content=content,
            created_by=request.user
        )
        messages.success(request, "Announcement posted successfully.")
        return redirect('communications:announcement_board')

    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')
    return render(request, "communications/k3ann_board.html", {
        "active_nav": "communications",
        "announcements": announcements
    })

@login_required(login_url='accounts:login')
def birthday_messages_view(request):
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        member = Member.objects.filter(id=member_id).first()
        if member:
            OutgoingMessage.objects.create(
                recipient_group=member.get_full_name(),
                message_type='SMS',
                subject='Happy Birthday',
                content=f"Happy Birthday {member.get_full_name()}! The Methodist Church Ghana society wishes you divine blessings on your special day."
            )
            messages.success(request, f"Birthday SMS sent to {member.get_full_name()}.")
            return redirect('communications:birthday_messages')

    current_month = datetime.date.today().month
    birthday_members = Member.objects.filter(date_of_birth__month=current_month)

    return render(request, "communications/k4birthday_message.html", {
        "active_nav": "communications",
        "birthday_members": birthday_members,
        "current_month_name": datetime.date.today().strftime('%B')
    })

@login_required(login_url='accounts:login')
def reminder_due_notice_view(request):
    if request.method == 'POST':
        group = request.POST.get('group', 'Pending Dues')
        message_text = request.POST.get('message_text', '').strip()
        OutgoingMessage.objects.create(
            recipient_group=group,
            message_type='SMS',
            subject='Welfare Dues Reminder',
            content=message_text or "Reminder: Please kindly settle your outstanding welfare dues for the current month. Thank you."
        )
        messages.success(request, "Welfare dues reminder notices broadcasted via SMS.")
        return redirect('communications:reminder_due_notice')

    pending_members = Member.objects.filter(status='PENDING')

    return render(request, "communications/k5reminder_due_notice.html", {
        "active_nav": "communications",
        "pending_members": pending_members
    })
