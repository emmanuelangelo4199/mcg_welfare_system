from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Meeting, ActionItem

User = get_user_model()

@login_required(login_url='accounts:login')
def meeting_list_view(request):
    meetings = Meeting.objects.all().order_by('-date')
    return render(request, "meetings/meeting_list.html", {
        "active_nav": "meetings",
        "meetings": meetings
    })

@login_required(login_url='accounts:login')
def meeting_schedule_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        location = request.POST.get('location', 'Church Hall').strip()
        agenda = request.POST.get('agenda', '').strip()

        Meeting.objects.create(
            title=title,
            date=date,
            start_time=start_time,
            location=location,
            agenda=agenda
        )
        messages.success(request, f"Meeting '{title}' scheduled successfully.")
        return redirect('meetings:meeting_list')

    return render(request, "meetings/meeting_schedule.html", {"active_nav": "meetings"})

@login_required(login_url='accounts:login')
def meeting_details_view(request):
    meeting_id = request.GET.get('id')
    meeting = get_object_or_404(Meeting, id=meeting_id) if meeting_id else Meeting.objects.first()
    return render(request, "meetings/meeting_details.html", {
        "active_nav": "meetings",
        "meeting": meeting
    })

@login_required(login_url='accounts:login')
def meeting_minutes_editor_view(request):
    if request.method == 'POST':
        meeting_id = request.POST.get('meeting_id')
        minutes = request.POST.get('minutes', '').strip()

        meeting = get_object_or_404(Meeting, id=meeting_id) if meeting_id else Meeting.objects.first()
        if meeting:
            meeting.minutes = minutes
            meeting.save()
            messages.success(request, f"Minutes for '{meeting.title}' saved.")
            return redirect('meetings:meeting_list')

    meetings = Meeting.objects.all()
    return render(request, "meetings/meeting_min_editor.html", {
        "active_nav": "meetings",
        "meetings": meetings
    })

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

        return redirect('meetings:action_items')

    items = ActionItem.objects.select_related('meeting', 'assigned_to').all().order_by('-due_date')
    meetings = Meeting.objects.all()
    users = User.objects.all()

    return render(request, "meetings/action_item_tracker.html", {
        "active_nav": "meetings",
        "action_items": items,
        "meetings": meetings,
        "users": users
    })
