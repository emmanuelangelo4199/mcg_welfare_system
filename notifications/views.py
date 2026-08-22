from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from .models import SystemNotification


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

@login_required(login_url='accounts:login')
def notification_settings_view(request):
    return render(request, "notifications/notifi_setting.html", {"active_nav": "notifications"})
