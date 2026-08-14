from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg
from .models import ServiceAttendance, ClassAttendanceRecord, OrganisationAttendanceRecord
from services.models import ChurchService
from classes.models import ClassGroup
from organisations.models import Organisation
from members.models import Member
import datetime

@login_required(login_url='accounts:login')
def overview_view(request):
    service_attendances = ServiceAttendance.objects.select_related('service').all().order_by('-recorded_at')[:10]
    total_att = ServiceAttendance.objects.aggregate(total=Sum('total_count'))['total'] or 0
    avg_att = ServiceAttendance.objects.aggregate(avg=Avg('total_count'))['avg'] or 0

    return render(request, "attendance/attendance_overview.html", {
        "active_nav": "attendance",
        "service_attendances": service_attendances,
        "total_att": total_att,
        "avg_att": round(avg_att, 1)
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
            att = ServiceAttendance.objects.create(
                service=service,
                male_count=males,
                female_count=females,
                children_count=children
            )
            messages.success(request, f"Recorded attendance of {att.total_count} for service '{service.title}'.")
            return redirect('attendance:overview')

    services = ChurchService.objects.all().order_by('-service_date')
    return render(request, "attendance/service_att.html", {
        "active_nav": "attendance",
        "services": services
    })

@login_required(login_url='accounts:login')
def class_attendance_view(request):
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        att_date = request.POST.get('date', str(datetime.date.today()))
        present_member_ids = request.POST.getlist('present_members')
        remarks = request.POST.get('remarks', '').strip()

        class_group = get_object_or_404(ClassGroup, id=class_id) if class_id else ClassGroup.objects.first()
        if class_group:
            record = ClassAttendanceRecord.objects.create(
                class_group=class_group,
                date=att_date,
                remarks=remarks
            )
            if present_member_ids:
                record.present_members.set(present_member_ids)
            messages.success(request, f"Class attendance for '{class_group.name}' recorded for {att_date}.")
            return redirect('attendance:overview')

    classes = ClassGroup.objects.all()
    members = Member.objects.filter(status='ACTIVE')
    records = ClassAttendanceRecord.objects.select_related('class_group').all().order_by('-date')[:10]

    return render(request, "attendance/class_att.html", {
        "active_nav": "attendance",
        "classes": classes,
        "members": members,
        "records": records
    })

@login_required(login_url='accounts:login')
def org_attendance_view(request):
    if request.method == 'POST':
        org_id = request.POST.get('org_id')
        att_date = request.POST.get('date', str(datetime.date.today()))
        attendees_count = int(request.POST.get('attendees_count', 0))
        remarks = request.POST.get('remarks', '').strip()

        org = get_object_or_404(Organisation, id=org_id) if org_id else Organisation.objects.first()
        if org:
            OrganisationAttendanceRecord.objects.create(
                organisation=org,
                date=att_date,
                attendees_count=attendees_count,
                remarks=remarks
            )
            messages.success(request, f"Organisation attendance of {attendees_count} recorded for '{org.name}'.")
            return redirect('attendance:overview')

    organisations = Organisation.objects.all()
    records = OrganisationAttendanceRecord.objects.select_related('organisation').all().order_by('-date')[:10]

    return render(request, "attendance/org_attendance.html", {
        "active_nav": "attendance",
        "organisations": organisations,
        "records": records
    })

@login_required(login_url='accounts:login')
def absentee_report_view(request):
    pending_members = Member.objects.filter(status='PENDING')
    return render(request, "attendance/abstee_report.html", {
        "active_nav": "attendance",
        "absentees": pending_members
    })
