from django.shortcuts import render

def upcoming_events_view(request):
    return render(request, "services/f5upcomingevents.html")

def event_calendar_view(request):
    return render(request, "services/event_calendar.html")

def service_program_form_view(request):
    return render(request, "services/f2service_program_form.html")

def service_detail_view(request):
    return render(request, "services/f3service_detail.html")

def service_attendance_view(request):
    return render(request, "services/f4serice_attendance.html")
