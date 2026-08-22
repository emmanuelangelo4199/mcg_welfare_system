from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from .models import NotificationPreference, SystemNotification


# Catalogue of the notification preferences surfaced on the settings page.
# Each preference has two delivery channels (email / in-app) and an optional
# "sensitive" badge for high-priority events.
NOTIFICATION_PREFERENCE_GROUPS = [
    {
        'title': 'Membership & Welfare',
        'icon': 'group',
        'preferences': [
            {'key': 'member_pending_regularisation', 'title': 'New Member Pending Regularisation',
             'description': 'Alert when a new member joins and requires administrative approval.',
             'email_default': True, 'in_app_default': True, 'sensitive': False},
            {'key': 'member_regularised', 'title': 'Member Regularised',
             'description': 'Notifications for completed membership verification processes.',
             'email_default': False, 'in_app_default': True, 'sensitive': False},
            {'key': 'transfer_received', 'title': 'Transfer Received',
             'description': "When a member's record is transferred from another society.",
             'email_default': True, 'in_app_default': True, 'sensitive': False},
            {'key': 'welfare_case_opened', 'title': 'New Welfare Case Opened',
             'description': 'High-priority alerts for new pastoral care or financial aid requests.',
             'email_default': True, 'in_app_default': True, 'sensitive': True},
            {'key': 'welfare_case_updated', 'title': 'Welfare Case Updated',
             'description': 'Status changes or new notes added to existing welfare files.',
             'email_default': False, 'in_app_default': True, 'sensitive': False},
        ],
    },
    {
        'title': 'Finance',
        'icon': 'account_balance_wallet',
        'preferences': [
            {'key': 'expense_awaiting_approval', 'title': 'Expense Awaiting Approval',
             'description': 'Request notification for steward or treasurer approval actions.',
             'email_default': True, 'in_app_default': True, 'sensitive': False},
            {'key': 'expense_processed', 'title': 'Expense Approved or Rejected',
             'description': 'Notification to the initiator when a claim has been processed.',
             'email_default': True, 'in_app_default': True, 'sensitive': False},
            {'key': 'statutory_payment_due', 'title': 'Statutory Payment Due',
             'description': 'Reminders for conference assessments and other mandatory levies.',
             'email_default': True, 'in_app_default': False, 'sensitive': False},
        ],
    },
    {
        'title': 'Meetings & Reminders',
        'icon': 'groups',
        'preferences': [
            {'key': 'meeting_scheduled', 'title': "Leaders' Meeting Scheduled",
             'description': 'Notifications when a new Society, Circuit, or Diocesan meeting is set.',
             'email_default': True, 'in_app_default': True, 'sensitive': False},
            {'key': 'minutes_published', 'title': 'Minutes Published',
             'description': 'Alert when official minutes from the latest council are available for review.',
             'email_default': False, 'in_app_default': True, 'sensitive': False},
            {'key': 'birthday_today', 'title': 'Birthday Today',
             'description': 'Daily summary of members celebrating birthdays for pastoral outreach.',
             'email_default': False, 'in_app_default': True, 'sensitive': False},
        ],
    },
]


def _notifications_for(request):
    """Return the current user's notifications, newest first."""
    return SystemNotification.objects.filter(user=request.user)


def _board_redirect(request, keep_selection=False):
    """Redirect back to the inbox while preserving the active filters."""
    query = {}
    for key in ('filter', 'q'):
        value = request.POST.get(key) or request.GET.get(key)
        if value:
            query[key] = value
    if keep_selection:
        value = request.POST.get('id') or request.GET.get('id')
        if value:
            query['id'] = value

    url = reverse('notifications:notification_board')
    if query:
        url = f"{url}?{urlencode(query)}"
    return redirect(url)


@login_required(login_url='accounts:login')
def notification_board_view(request):
    notifications = _notifications_for(request)

    # Read / unread filter.
    filter_by = request.GET.get('filter', 'all')
    if filter_by == 'unread':
        notifications = notifications.filter(is_read=False)

    # Keyword search across title and message.
    query = request.GET.get('q', '').strip()
    if query:
        notifications = notifications.filter(
            Q(title__icontains=query) | Q(message__icontains=query)
        )

    # Detail pane selection (?id=). Selecting an unread item marks it read.
    selected = None
    selected_id = request.GET.get('id')
    if selected_id:
        selected = _notifications_for(request).filter(id=selected_id).first()
        if selected and not selected.is_read:
            selected.is_read = True
            selected.save(update_fields=['is_read'])

    context = {
        "active_nav": "notifications",
        "notifications": notifications,
        "unread_count": _notifications_for(request).filter(is_read=False).count(),
        "selected": selected,
        "filter_by": filter_by,
        "query": query,
    }
    return render(request, "notifications/notifi_board.html", context)


@login_required(login_url='accounts:login')
def notification_toggle_read(request, pk):
    notification = get_object_or_404(SystemNotification, pk=pk, user=request.user)
    notification.is_read = not notification.is_read
    notification.save(update_fields=['is_read'])

    if notification.is_read:
        messages.success(request, "Notification marked as read.")
    else:
        messages.info(request, "Notification marked as unread.")
    return _board_redirect(request, keep_selection=True)


@login_required(login_url='accounts:login')
def notification_delete(request, pk):
    if request.method == 'POST':
        notification = get_object_or_404(SystemNotification, pk=pk, user=request.user)
        notification.delete()
        messages.success(request, "Notification deleted.")
    return _board_redirect(request)


@login_required(login_url='accounts:login')
def notification_mark_all_read(request):
    if request.method == 'POST':
        updated = _notifications_for(request).filter(is_read=False).update(is_read=True)
        if updated:
            messages.success(request, f"{updated} notification(s) marked as read.")
        else:
            messages.info(request, "You have no unread notifications.")
    return _board_redirect(request)


@login_required(login_url='accounts:login')
def notification_clear_all(request):
    if request.method == 'POST':
        deleted, _ = _notifications_for(request).delete()
        if deleted:
            messages.success(request, f"{deleted} notification(s) cleared.")
        else:
            messages.info(request, "Your inbox is already empty.")
    return _board_redirect(request)


def _settings_groups(user):
    """Return the preference catalogue with the user's saved values merged in."""
    stored = {
        pref.key: pref
        for pref in NotificationPreference.objects.filter(user=user)
    }

    groups = []
    for group in NOTIFICATION_PREFERENCE_GROUPS:
        preferences = []
        for spec in group['preferences']:
            pref = stored.get(spec['key'])
            preferences.append({
                'key': spec['key'],
                'title': spec['title'],
                'description': spec['description'],
                'sensitive': spec['sensitive'],
                'email': pref.email if pref else spec['email_default'],
                'in_app': pref.in_app if pref else spec['in_app_default'],
            })
        groups.append({
            'title': group['title'],
            'icon': group['icon'],
            'preferences': preferences,
        })
    return groups


@login_required(login_url='accounts:login')
def notification_settings_view(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'reset':
            NotificationPreference.objects.filter(user=request.user).delete()
            messages.success(request, "Notification preferences reset to defaults.")
        else:
            for group in NOTIFICATION_PREFERENCE_GROUPS:
                for spec in group['preferences']:
                    key = spec['key']
                    NotificationPreference.objects.update_or_create(
                        user=request.user,
                        key=key,
                        defaults={
                            'email': f"pref_{key}_email" in request.POST,
                            'in_app': f"pref_{key}_inapp" in request.POST,
                        },
                    )
            messages.success(request, "Notification preferences saved.")
        return redirect('notifications:notification_settings')

    user = request.user
    profile = getattr(user, 'profile', None)
    if profile:
        role_label = profile.get_role_display()
    else:
        role_label = 'Administrator' if user.is_superuser else 'Society Member'

    context = {
        "active_nav": "notifications",
        "groups": _settings_groups(user),
        "display_name": user.get_full_name().strip() or user.username,
        "role_label": f"{role_label} Profile",
    }
    return render(request, "notifications/notifi_setting.html", context)
