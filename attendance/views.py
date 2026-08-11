from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ServiceAttendance, ClassAttendanceRecord
from services.models import ChurchService

@login_required(login_url='accounts:login')
def overview_view(request):
    service_attendances = ServiceAttendance.objects.select_related('service').all().order_by('-recorded_at')[:10]
    return render(request, "attendance/attendance_overview.html", {
        "active_nav": "attendance",
        "service_attendances": service_attendances
    })

@login_required(login_url='accounts:login')
def service_attendance_view(request):
    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        males = int(request.POST.get('male_count', 0))
        females = int(request.POST.get('female_count', 0))
        children = int(request.POST.get('children_count', 0))

        service = get_object_or_404(ChurchService, id=service_id) if service_id else ChurchService.objects.first()
        if service:
            ServiceAttendance.objects.create(
                service=service,
                male_count=males,
                female_count=females,
                children_count=children
            )
            messages.success(request, f"Attendance for {service.title} recorded.")
            return redirect('attendance:overview')

    services = ChurchService.objects.all()
    return render(request, "attendance/service_att.html", {
        "active_nav": "attendance",
        "services": services
    })

@login_required(login_url='accounts:login')
def class_attendance_view(request):
    return render(request, "attendance/class_att.html", {"active_nav": "attendance"})

@login_required(login_url='accounts:login')
def org_attendance_view(request):
    return render(request, "attendance/org_attendance.html", {"active_nav": "attendance"})

@login_required(login_url='accounts:login')
def absentee_report_view(request):
    return render(request, "attendance/abstee_report.html", {"active_nav": "attendance"})
