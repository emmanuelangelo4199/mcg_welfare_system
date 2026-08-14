from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ChurchService

@login_required(login_url='accounts:login')
def upcoming_events_view(request):
    services = ChurchService.objects.all().order_by('service_date')
    context = {
        "active_nav": "services",
        "services": services
    }
    return render(request, "services/f5upcomingevents.html", context)

@login_required(login_url='accounts:login')
def event_calendar_view(request):
    services = ChurchService.objects.all()
    context = {
        "active_nav": "services",
        "services": services
    }
    return render(request, "services/event_calendar.html", context)

@login_required(login_url='accounts:login')
def service_program_form_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        service_date = request.POST.get('service_date')
        start_time = request.POST.get('start_time')
        preacher = request.POST.get('preacher', '').strip()
        theme = request.POST.get('theme', '').strip()

        ChurchService.objects.create(
            title=title,
            service_date=service_date,
            start_time=start_time,
            preacher=preacher,
            theme=theme
        )
        messages.success(request, f"Service program '{title}' scheduled.")
        return redirect('services:upcoming_events') 
    context = {
        "active_nav": "services"
    }

    return render(request, "services/f2service_program_form.html", context)

@login_required(login_url='accounts:login')
def service_detail_view(request):
    service_id = request.GET.get('id')
    service = get_object_or_404(ChurchService, id=service_id) if service_id else ChurchService.objects.first()
    context = {
        "active_nav": "services",
        "service": service
    }
    return render(request, "services/f3service_detail.html", context)

@login_required(login_url='accounts:login')
def service_attendance_view(request):
    context = {
        "active_nav": "services"
    }
    return render(request, "services/f4serice_attendance.html", context)
