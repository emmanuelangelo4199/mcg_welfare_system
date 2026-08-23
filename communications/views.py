from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.core.paginator import Paginator
from django.utils import timezone
from core.models import AuditLog
from .models import Announcement, OutgoingMessage, MessageTemplate, CommunicationLog
from members.models import Member
import datetime


def ensure_default_templates():
    """Seed default message templates if none exist"""
    defaults = [
        {
            "code": "BIRTHDAY_SMS",
            "name": "Birthday SMS",
            "template_type": "BIRTHDAY",
            "message_type": "SMS",
            "subject": "Happy Birthday",
            "content": "Happy Birthday {{name}}! The Methodist Church Ghana society wishes you divine blessings on your special day. Age: {{age}}",
        },
        {
            "code": "DUE_REMINDER_SMS",
            "name": "Welfare Dues Reminder",
            "template_type": "DUE_REMINDER",
            "message_type": "SMS",
            "subject": "Welfare Dues Reminder",
            "content": "Reminder: Dear {{name}}, please kindly settle your outstanding welfare dues of GHS {{amount}} for {{month}}. Thank you.",
        },
        {
            "code": "WELFARE_SUPPORT",
            "name": "Welfare Support Notification",
            "template_type": "WELFARE",
            "message_type": "SMS",
            "content": "Dear {{name}}, your welfare case '{{title}}' status is now {{status}}. Approved amount: GHS {{amount}}.",
        },
        {
            "code": "GENERAL_ANNOUNCEMENT",
            "name": "General Announcement",
            "template_type": "ANNOUNCEMENT",
            "message_type": "EMAIL",
            "subject": "{{title}}",
            "content": "{{content}}",
        },
    ]
    for tmpl in defaults:
        MessageTemplate.objects.get_or_create(code=tmpl["code"], defaults=tmpl)


@login_required(login_url='accounts:login')
def compose_message_view(request):
    ensure_default_templates()
    templates = MessageTemplate.objects.filter(is_active=True).order_by('template_type', 'name')
    members = Member.objects.filter(status='ACTIVE').order_by('first_name')[:200]

    # Stats
    total_messages = OutgoingMessage.objects.count()
    sms_count = OutgoingMessage.objects.filter(message_type='SMS').count()
    email_count = OutgoingMessage.objects.filter(message_type='EMAIL').count()

    if request.method == 'POST':
        action = request.POST.get('action', 'send')
        msg_type = request.POST.get('type', 'SMS')
        group = request.POST.get('recipient_group', 'All Members')
        subject = request.POST.get('subject', '').strip()
        content = request.POST.get('content', '').strip()
        template_code = request.POST.get('template_code')
        recipient_count = request.POST.get('recipient_count')

        if not content:
            messages.error(request, "Message content is required.")
            return redirect('communications:compose_message')

        try:
            recipient_count = int(recipient_count) if recipient_count else 0
        except ValueError:
            recipient_count = 0

        # If no count provided, estimate from group
        if recipient_count == 0:
            if group == 'All Members':
                recipient_count = Member.objects.filter(status='ACTIVE').count()
            elif 'Class' in group:
                recipient_count = Member.objects.filter(status='ACTIVE').count() // 4
            else:
                recipient_count = 1

        with transaction.atomic():
            out_msg = OutgoingMessage.objects.create(
                recipient_group=group,
                recipient_count=recipient_count,
                message_type=msg_type,
                subject=subject,
                content=content,
                status='SENT',
                created_by=request.user,
            )

            # Create delivery logs for demo (first 5 members)
            for m in Member.objects.filter(status='ACTIVE')[:5]:
                CommunicationLog.objects.create(
                    outgoing_message=out_msg,
                    recipient_name=m.get_full_name(),
                    recipient_contact=m.phone_number or m.email or '',
                    status='SENT',
                )

            AuditLog.objects.create(
                user=request.user,
                action=f"Sent {msg_type} to {group}",
                model_name="OutgoingMessage",
                object_id=str(out_msg.id),
                details=f"Subject: {subject}, Recipients: {recipient_count}",
            )

        messages.success(request, f"{msg_type} message sent to {group} ({recipient_count} recipients).")
        return redirect('communications:message_history')

    context = {
        "active_nav": "communications",
        "templates": templates,
        "members": members,
        "total_messages": total_messages,
        "sms_count": sms_count,
        "email_count": email_count,
    }
    return render(request, "communications/compose_msg.html", context)


@login_required(login_url='accounts:login')
def message_history_view(request):
    ensure_default_templates()
    messages_qs = OutgoingMessage.objects.select_related('created_by').all()

    q = request.GET.get('q', '').strip()
    msg_type = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if q:
        messages_qs = messages_qs.filter(
            models.Q(recipient_group__icontains=q)
            | models.Q(subject__icontains=q)
            | models.Q(content__icontains=q)
        )

    if msg_type:
        messages_qs = messages_qs.filter(message_type=msg_type)

    if status_filter:
        messages_qs = messages_qs.filter(status=status_filter)

    # Stats
    total = OutgoingMessage.objects.count()
    sent = OutgoingMessage.objects.filter(status='SENT').count()
    failed = OutgoingMessage.objects.filter(status='FAILED').count()

    paginator = Paginator(messages_qs.order_by('-sent_at'), 15)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)

    context = {
        "active_nav": "communications",
        "messages_list": messages_page,
        "messages_page": messages_page,
        "paginator": paginator,
        "q": q,
        "type_filter": msg_type,
        "status_filter": status_filter,
        "total": total,
        "sent": sent,
        "failed": failed,
        "type_choices": OutgoingMessage.MESSAGE_TYPE_CHOICES,
        "status_choices": OutgoingMessage.STATUS_CHOICES,
        "filtered_count": messages_qs.count(),
    }
    return render(request, "communications/k2msg_history.html", context)


@login_required(login_url='accounts:login')
def announcement_board_view(request):
    ensure_default_templates()
    announcements_qs = Announcement.objects.select_related('created_by').all()

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    active_filter = request.GET.get('active', '').strip()

    if q:
        announcements_qs = announcements_qs.filter(
            models.Q(title__icontains=q) | models.Q(content__icontains=q)
        )

    if category:
        announcements_qs = announcements_qs.filter(category=category)

    if active_filter == 'active':
        announcements_qs = announcements_qs.filter(is_active=True)
    elif active_filter == 'inactive':
        announcements_qs = announcements_qs.filter(is_active=False)

    if request.method == 'POST':
        action = request.POST.get('action', 'create')

        if action == 'create':
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '').strip()
            category_val = request.POST.get('category', 'GENERAL')
            priority = request.POST.get('priority', 'MEDIUM')
            is_pinned = request.POST.get('is_pinned') == 'on'
            expiry_date = request.POST.get('expiry_date')

            if not title or not content:
                messages.error(request, "Title and content are required.")
                return redirect('communications:announcement_board')

            with transaction.atomic():
                ann = Announcement.objects.create(
                    title=title,
                    content=content,
                    category=category_val,
                    priority=priority,
                    is_pinned=is_pinned,
                    expiry_date=expiry_date if expiry_date else None,
                    created_by=request.user,
                )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Posted announcement {ann.id}",
                    model_name="Announcement",
                    object_id=str(ann.id),
                    details=f"Title: {title}, Category: {category_val}",
                )

            messages.success(request, "Announcement posted successfully.")
            return redirect('communications:announcement_board')

        elif action == 'toggle_active':
            ann_id = request.POST.get('announcement_id')
            ann = get_object_or_404(Announcement, id=ann_id)
            ann.is_active = not ann.is_active
            ann.save(update_fields=['is_active', 'updated_at'])
            messages.success(request, f"Announcement {'activated' if ann.is_active else 'deactivated'}.")
            return redirect('communications:announcement_board')

        elif action == 'delete':
            ann_id = request.POST.get('announcement_id')
            ann = get_object_or_404(Announcement, id=ann_id)
            title = ann.title
            ann.delete()
            AuditLog.objects.create(
                user=request.user,
                action=f"Deleted announcement {title}",
                model_name="Announcement",
                object_id=str(ann_id),
            )
            messages.success(request, f"Announcement '{title}' deleted.")
            return redirect('communications:announcement_board')

    paginator = Paginator(announcements_qs.order_by('-is_pinned', '-created_at'), 10)
    page_number = request.GET.get('page')
    announcements_page = paginator.get_page(page_number)

    context = {
        "active_nav": "communications",
        "announcements": announcements_page,
        "announcements_page": announcements_page,
        "paginator": paginator,
        "q": q,
        "category_filter": category,
        "active_filter": active_filter,
        "category_choices": Announcement.CATEGORY_CHOICES,
        "priority_choices": Announcement.PRIORITY_CHOICES,
        "total_announcements": Announcement.objects.count(),
        "active_announcements": Announcement.objects.filter(is_active=True).count(),
        "filtered_count": announcements_qs.count(),
    }
    return render(request, "communications/k3ann_board.html", context)


@login_required(login_url='accounts:login')
def birthday_messages_view(request):
    ensure_default_templates()
    template_obj = MessageTemplate.objects.filter(code='BIRTHDAY_SMS').first()

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        custom_message = request.POST.get('custom_message', '').strip()

        member = Member.objects.filter(id=member_id).first()
        if member:
            # Calculate age if DOB exists
            age = ''
            if member.date_of_birth:
                today = datetime.date.today()
                age = today.year - member.date_of_birth.year - ((today.month, today.day) < (member.date_of_birth.month, member.date_of_birth.day))

            if custom_message:
                content = custom_message
            elif template_obj:
                content = template_obj.content.replace('{{name}}', member.get_full_name()).replace('{{age}}', str(age))
            else:
                content = f"Happy Birthday {member.get_full_name()}! The Methodist Church Ghana society wishes you divine blessings on your special day."

            with transaction.atomic():
                out_msg = OutgoingMessage.objects.create(
                    recipient_group=member.get_full_name(),
                    recipient_count=1,
                    message_type='SMS',
                    subject='Happy Birthday',
                    content=content,
                    status='SENT',
                    created_by=request.user,
                )

                CommunicationLog.objects.create(
                    outgoing_message=out_msg,
                    recipient_name=member.get_full_name(),
                    recipient_contact=member.phone_number or '',
                    status='SENT',
                )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Sent birthday SMS to {member.get_full_name()}",
                    model_name="OutgoingMessage",
                    object_id=str(out_msg.id),
                )

            messages.success(request, f"Birthday SMS sent to {member.get_full_name()}.")
            return redirect('communications:birthday_messages')

    current_month = datetime.date.today().month
    current_month_name = datetime.date.today().strftime('%B')

    birthday_members = Member.objects.filter(date_of_birth__month=current_month).order_by('date_of_birth__day')
    upcoming_birthdays = Member.objects.filter(date_of_birth__month__in=[current_month, (current_month % 12) + 1]).order_by('date_of_birth__month', 'date_of_birth__day')[:20]

    # All members with birthdays for search
    all_members = Member.objects.exclude(date_of_birth__isnull=True).order_by('first_name')[:100]

    # Stats
    total_birthdays_month = birthday_members.count()
    today_birthdays = Member.objects.filter(date_of_birth__month=current_month, date_of_birth__day=datetime.date.today().day).count()

    context = {
        "active_nav": "communications",
        "birthday_members": birthday_members,
        "upcoming_birthdays": upcoming_birthdays,
        "all_members": all_members,
        "current_month_name": current_month_name,
        "current_month": current_month,
        "total_birthdays_month": total_birthdays_month,
        "today_birthdays": today_birthdays,
        "template": template_obj,
    }
    return render(request, "communications/k4birthday_message.html", context)


@login_required(login_url='accounts:login')
def reminder_due_notice_view(request):
    ensure_default_templates()
    template_obj = MessageTemplate.objects.filter(code='DUE_REMINDER_SMS').first()

    pending_members_qs = Member.objects.filter(status='PENDING')
    # For demo, also consider members without recent payment? Use all active as pending dues
    dues_pending = Member.objects.filter(status='ACTIVE').order_by('first_name')[:50]

    q = request.GET.get('q', '').strip()
    if q:
        dues_pending = dues_pending.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q) | models.Q(phone_number__icontains=q)
        )

    if request.method == 'POST':
        action = request.POST.get('action', 'broadcast')
        group = request.POST.get('group', 'Pending Dues')
        message_text = request.POST.get('message_text', '').strip()
        selected_members = request.POST.getlist('selected_members')
        amount = request.POST.get('amount', '').strip()
        month = request.POST.get('month', datetime.date.today().strftime('%B %Y'))

        if not message_text:
            if template_obj:
                message_text = template_obj.content
            else:
                message_text = "Reminder: Please kindly settle your outstanding welfare dues for the current month. Thank you."

        recipient_count = len(selected_members) if selected_members else dues_pending.count()

        with transaction.atomic():
            out_msg = OutgoingMessage.objects.create(
                recipient_group=group,
                recipient_count=recipient_count,
                message_type='SMS',
                subject='Welfare Dues Reminder',
                content=message_text,
                status='SENT',
                created_by=request.user,
            )

            # Create logs for selected or all
            target_members = Member.objects.filter(id__in=selected_members) if selected_members else dues_pending[:20]
            for m in target_members:
                personalized = message_text.replace('{{name}}', m.get_full_name()).replace('{{amount}}', amount or '0').replace('{{month}}', month)
                CommunicationLog.objects.create(
                    outgoing_message=out_msg,
                    recipient_name=m.get_full_name(),
                    recipient_contact=m.phone_number or '',
                    status='SENT',
                )

            AuditLog.objects.create(
                user=request.user,
                action=f"Broadcasted dues reminder to {group}",
                model_name="OutgoingMessage",
                object_id=str(out_msg.id),
                details=f"Recipients: {recipient_count}, Group: {group}",
            )

        messages.success(request, f"Welfare dues reminder broadcasted to {recipient_count} members via SMS.")
        return redirect('communications:reminder_due_notice')

    paginator = Paginator(dues_pending, 15)
    page_number = request.GET.get('page')
    pending_page = paginator.get_page(page_number)

    context = {
        "active_nav": "communications",
        "pending_members": pending_members_qs,
        "dues_pending": pending_page,
        "dues_page": pending_page,
        "paginator": paginator,
        "q": q,
        "template": template_obj,
        "total_pending": pending_members_qs.count(),
        "filtered_count": dues_pending.count() if hasattr(dues_pending, 'count') else 0,
    }
    return render(request, "communications/k5reminder_due_notice.html", context)