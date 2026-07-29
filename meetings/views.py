from django.shortcuts import render

def meeting_list_view(request):
    return render(request, "meetings/meeting_list.html")

def meeting_schedule_view(request):
    return render(request, "meetings/meeting_schedule.html")

def meeting_details_view(request):
    return render(request, "meetings/meeting_details.html")

def meeting_minutes_editor_view(request):
    return render(request, "meetings/meeting_min_editor.html")

def action_item_tracker_view(request):
    return render(request, "meetings/action_item_tracker.html")
