from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from .models import Meeting, ActionItem

User = get_user_model()

DEFAULT_AGENDA_ITEMS = ["Opening Prayer", "Minutes of the Last Meeting"]

@login_required(login_url='accounts:login')
def meeting_list_view(request):
    meetings = Meeting.objects.all().order_by('-date')
    return render(request, "meetings/meeting_list.html", {
        "active_nav": "meetings",
        "meetings": meetings
    })

def _build_agenda(request):
    """Combine the repeatable agenda item inputs and the notes box into one agenda text."""
    items = [item.strip() for item in request.POST.getlist('agenda_items') if item.strip()]
    agenda = "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))

    if not agenda:
        agenda = request.POST.get('agenda', '').strip()

    notes = request.POST.get('notes', '').strip()
    if notes:
        agenda = f"{agenda}\n\nNotes:\n{notes}" if agenda else f"Notes:\n{notes}"

    return agenda

@login_required(login_url='accounts:login')
def meeting_schedule_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        date = request.POST.get('date', '').strip()
        start_time = request.POST.get('start_time', '').strip()
        location = request.POST.get('location', '').strip() or 'Church Hall'
        agenda = _build_agenda(request)

        if not (title and date and start_time):
            submitted_items = [i for i in request.POST.getlist('agenda_items') if i.strip()]
            messages.error(request, "Meeting type, date and time are required.")
            return render(request, "meetings/meeting_schedule.html", {
                "active_nav": "meetings",
                "form_data": request.POST,
                "agenda_items": submitted_items or DEFAULT_AGENDA_ITEMS,
            })


        Meeting.objects.create(
            title=title,
            date=date,
            start_time=start_time,
            location=location,
            agenda=agenda
        )
        messages.success(request, f"Meeting '{title}' scheduled successfully.")
        return redirect('meetings:meeting_list')
    context = {
        "active_nav": "meetings",
        "agenda_items": DEFAULT_AGENDA_ITEMS,
    }
    return render(request, "meetings/meeting_schedule.html", context)

@login_required(login_url='accounts:login')
def meeting_details_view(request):
    meeting_id = request.GET.get('id')
    if meeting_id:
        meeting = get_object_or_404(Meeting, id=meeting_id)
    else:
        meeting = Meeting.objects.order_by('-date', '-start_time').first()

    agenda_lines = []
    action_items = []

    if meeting:
        agenda_lines = [line.strip() for line in (meeting.agenda or '').splitlines() if line.strip()]

        today = timezone.localdate()
        action_items = list(
            meeting.action_items.select_related('assigned_to').order_by('is_completed', 'due_date')
        )
        for item in action_items:
            item.is_overdue = not item.is_completed and item.due_date < today

    context = {
        "active_nav": "meetings",
        "meeting": meeting,
        "agenda_lines": agenda_lines,
        "action_items": action_items,
        "open_action_count": sum(1 for item in action_items if not item.is_completed),
    }
    return render(request, "meetings/meeting_details.html", context)

@login_required(login_url='accounts:login')
def meeting_minutes_editor_view(request):
    if request.method == 'POST':
        meeting_id = request.POST.get('meeting_id')
        meeting = get_object_or_404(Meeting, id=meeting_id) if meeting_id else None

        if not meeting:
            messages.error(request, "Select a meeting before saving minutes.")
            return redirect('meetings:meeting_minutes_editor')

        meeting.minutes = request.POST.get('minutes', '').strip()
        meeting.save()

        task = request.POST.get('task', '').strip()
        due_date = request.POST.get('due_date', '').strip()

        if task and due_date:
            assigned_id = request.POST.get('assigned_to')
            ActionItem.objects.create(
                meeting=meeting,
                task=task,
                due_date=due_date,
                assigned_to=User.objects.filter(id=assigned_id).first() if assigned_id else None,
            )
            messages.success(request, f"Minutes saved and action item '{task}' created.")
        elif task:
            messages.warning(request, "Minutes saved, but the action item needs a due date to be recorded.")
        else:
            messages.success(request, f"Minutes for '{meeting.title}' saved.")

        target = 'meetings:meeting_details' if request.POST.get('next') == 'details' else 'meetings:meeting_minutes_editor'
        return redirect(f"{reverse(target)}?id={meeting.id}")

    meeting_id = request.GET.get('id')
    if meeting_id:
        meeting = get_object_or_404(Meeting, id=meeting_id)
    else:
        meeting = Meeting.objects.order_by('-date', '-start_time').first()

    agenda_lines = []
    if meeting:
        agenda_lines = [line.strip() for line in (meeting.agenda or '').splitlines() if line.strip()]

    context = {
        "active_nav": "meetings",
        "meeting": meeting,
        "meetings": Meeting.objects.order_by('-date'),
        "agenda_lines": agenda_lines,
        "users": User.objects.all(),
    }
    return render(request, "meetings/meeting_min_editor.html", context)

@login_required(login_url='accounts:login')
def action_item_tracker_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ActionItem, id=item_id)
            item.is_completed = not item.is_completed
            item.save()
            messages.success(request, f"Updated task status for '{item.task}'.")
        elif action == 'create':
            meeting_id = request.POST.get('meeting_id')
            task = request.POST.get('task', '').strip()
            due_date = request.POST.get('due_date')
            assigned_user_id = request.POST.get('assigned_to')

            meeting = get_object_or_404(Meeting, id=meeting_id) if meeting_id else Meeting.objects.first()
            assigned_user = User.objects.filter(id=assigned_user_id).first() if assigned_user_id else None

            if meeting and task and due_date:
                ActionItem.objects.create(
                    meeting=meeting,
                    task=task,
                    due_date=due_date,
                    assigned_to=assigned_user
                )
                messages.success(request, f"Action item '{task}' assigned.")

        return redirect('meetings:action_item_tracker')

    today = timezone.localdate()
    items = ActionItem.objects.select_related('meeting', 'assigned_to').order_by('is_completed', 'due_date')

    status = request.GET.get('status', '')
    person = request.GET.get('person', '').strip()
    due_from = request.GET.get('due_from', '').strip()
    due_to = request.GET.get('due_to', '').strip()

    if status == 'completed':
        items = items.filter(is_completed=True)
    elif status == 'overdue':
        items = items.filter(is_completed=False, due_date__lt=today)
    elif status == 'open':
        items = items.filter(is_completed=False, due_date__gte=today)

    if person:
        items = items.filter(
            Q(assigned_to__first_name__icontains=person)
            | Q(assigned_to__last_name__icontains=person)
            | Q(assigned_to__username__icontains=person)
        )
    if due_from:
        items = items.filter(due_date__gte=due_from)
    if due_to:
        items = items.filter(due_date__lte=due_to)

    items = list(items)
    for item in items:
        item.is_overdue = not item.is_completed and item.due_date < today

    all_items = ActionItem.objects.all()

    context = {
        "active_nav": "meetings",
        "action_items": items,
        "meetings": Meeting.objects.all(),
        "users": User.objects.all(),
        "today": today,
        "open_count": all_items.filter(is_completed=False, due_date__gte=today).count(),
        "overdue_count": all_items.filter(is_completed=False, due_date__lt=today).count(),
        "completed_count": all_items.filter(is_completed=True).count(),
        "filters": {
            "status": status,
            "person": person,
            "due_from": due_from,
            "due_to": due_to,
        },
    }

    return render(request, "meetings/action_item_tracker.html", context)
