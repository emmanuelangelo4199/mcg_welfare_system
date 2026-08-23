from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Sum, Avg, Count
from django.core.paginator import Paginator
from django.utils import timezone
from core.models import AuditLog
from .models import ServiceAttendance, ClassAttendanceRecord, OrganisationAttendanceRecord, AttendanceSummary, AbsenteeFollowUp
from services.models import ChurchService
from classes.models import ClassGroup
from organisations.models import Organisation
from members.models import Member
import datetime


@login_required(login_url='accounts:login')
def overview_view(request):
    today = timezone.now().date()
    week_ago = today - datetime.timedelta(days=7)
    month_ago = today - datetime.timedelta(days=30)

    # Aggregates
    service_attendances = ServiceAttendance.objects.select_related('service').all().order_by('-recorded_at')
    total_att = ServiceAttendance.objects.aggregate(total=Sum('total_count'))['total'] or 0
    avg_att = ServiceAttendance.objects.aggregate(avg=Avg('total_count'))['avg'] or 0
    week_total = ServiceAttendance.objects.filter(service_date__gte=week_ago).aggregate(total=Sum('total_count'))['total'] or 0

    class_records = ClassAttendanceRecord.objects.select_related('class_group').all().order_by('-date')
    org_records = OrganisationAttendanceRecord.objects.select_related('organisation').all().order_by('-date')

    # Recent
    recent_service = service_attendances[:10]
    recent_class = class_records[:10]
    recent_org = org_records[:10]

    # Stats
    total_service_records = ServiceAttendance.objects.count()
    total_class_records = ClassAttendanceRecord.objects.count()
    total_org_records = OrganisationAttendanceRecord.objects.count()
    total_absentees = AbsenteeFollowUp.objects.filter(follow_up_status='PENDING').count()

    # Top classes by attendance rate
    top_classes = []
    for rec in class_records[:20]:
        try:
            top_classes.append({
                'name': rec.class_group.name,
                'rate': rec.attendance_rate,
                'present': rec.present_count,
                'date': rec.date,
            })
        except Exception:
            continue
    top_classes = sorted(top_classes, key=lambda x: x['rate'], reverse=True)[:5]

    # Monthly trend (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_date = today - datetime.timedelta(days=30*i)
        month_total = ServiceAttendance.objects.filter(
            service_date__month=month_date.month,
            service_date__year=month_date.year
        ).aggregate(total=Sum('total_count'))['total'] or 0
        monthly_data.append({
            'label': month_date.strftime('%b'),
            'total': month_total,
        })

    context = {
        "active_nav": "attendance",
        "service_attendances": recent_service,
        "class_records": recent_class,
        "org_records": recent_org,
        "total_att": total_att,
        "avg_att": round(avg_att, 1),
        "week_total": week_total,
        "total_service_records": total_service_records,
        "total_class_records": total_class_records,
        "total_org_records": total_org_records,
        "total_absentees": total_absentees,
        "top_classes": top_classes,
        "monthly_data": monthly_data,
        "today": today,
    }
    return render(request, "attendance/attendance_overview.html", context)


@login_required(login_url='accounts:login')
def service_attendance_view(request):
    services = ChurchService.objects.all().order_by('-service_date')
    attendances_qs = ServiceAttendance.objects.select_related('service', 'recorded_by').all()

    q = request.GET.get('q', '').strip()
    date_filter = request.GET.get('date', '').strip()

    if q:
        attendances_qs = attendances_qs.filter(
            models.Q(service__title__icontains=q) | models.Q(notes__icontains=q)
        )

    if date_filter:
        try:
            filter_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            attendances_qs = attendances_qs.filter(service_date=filter_date)
        except ValueError:
            pass

    # Stats
    total_records = ServiceAttendance.objects.count()
    total_attendance = ServiceAttendance.objects.aggregate(total=Sum('total_count'))['total'] or 0
    avg_attendance = ServiceAttendance.objects.aggregate(avg=Avg('total_count'))['avg'] or 0

    paginator = Paginator(attendances_qs.order_by('-service_date', '-recorded_at'), 15)
    page_number = request.GET.get('page')
    attendances_page = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        service_id = request.POST.get('service_id')
        service_date = request.POST.get('service_date')
        males = request.POST.get('male_count', '0')
        females = request.POST.get('female_count', '0')
        children = request.POST.get('children_count', '0')
        notes = request.POST.get('notes', '').strip()

        try:
            males = int(males)
            females = int(females)
            children = int(children)
            if males < 0 or females < 0 or children < 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Attendance counts must be non-negative integers.")
            return redirect('attendance:service_attendance')

        service = None
        if service_id:
            service = get_object_or_404(ChurchService, id=service_id)
        else:
            service = ChurchService.objects.first()

        if not service:
            messages.error(request, "Please create a church service first.")
            return redirect('services:service_program_form')

        with transaction.atomic():
            if action == 'edit':
                att_id = request.POST.get('attendance_id')
                att = get_object_or_404(ServiceAttendance, id=att_id)
                att.service = service
                att.service_date = service_date if service_date else service.service_date
                att.male_count = males
                att.female_count = females
                att.children_count = children
                att.notes = notes
                att.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Updated service attendance {att.id}",
                    model_name="ServiceAttendance",
                    object_id=str(att.id),
                    details=f"Service: {service.title}, Total: {att.total_count}",
                )
                messages.success(request, f"Attendance updated to {att.total_count} for '{service.title}'.")
            else:
                att = ServiceAttendance.objects.create(
                    service=service,
                    service_date=service_date if service_date else service.service_date,
                    male_count=males,
                    female_count=females,
                    children_count=children,
                    notes=notes,
                    recorded_by=request.user,
                )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Recorded service attendance {att.id}",
                    model_name="ServiceAttendance",
                    object_id=str(att.id),
                    details=f"Service: {service.title}, Total: {att.total_count}",
                )
                messages.success(request, f"Recorded attendance of {att.total_count} for service '{service.title}'.")

            return redirect('attendance:overview')

    context = {
        "active_nav": "attendance",
        "services": services,
        "attendances": attendances_page,
        "attendances_page": attendances_page,
        "paginator": paginator,
        "q": q,
        "date_filter": date_filter,
        "total_records": total_records,
        "total_attendance": total_attendance,
        "avg_attendance": round(avg_attendance, 1),
        "filtered_count": attendances_qs.count(),
    }
    return render(request, "attendance/service_att.html", context)


@login_required(login_url='accounts:login')
def class_attendance_view(request):
    classes = ClassGroup.objects.all().order_by('name')
    members = Member.objects.filter(status='ACTIVE').order_by('first_name', 'last_name')
    records_qs = ClassAttendanceRecord.objects.select_related('class_group', 'recorded_by').all()

    q = request.GET.get('q', '').strip()
    class_filter = request.GET.get('class_filter', '').strip()
    date_filter = request.GET.get('date', '').strip()

    if q:
        records_qs = records_qs.filter(
            models.Q(class_group__name__icontains=q) | models.Q(remarks__icontains=q)
        )

    if class_filter:
        records_qs = records_qs.filter(class_group_id=class_filter)

    if date_filter:
        try:
            filter_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            records_qs = records_qs.filter(date=filter_date)
        except ValueError:
            pass

    # Stats
    total_records = ClassAttendanceRecord.objects.count()
    avg_present = 0
    if records_qs.exists():
        # Calculate average present count
        total_present = sum(r.present_count for r in records_qs[:50])
        avg_present = total_present / min(50, records_qs.count())

    paginator = Paginator(records_qs.order_by('-date', '-created_at'), 15)
    page_number = request.GET.get('page')
    records_page = paginator.get_page(page_number)

    # For form: get members of selected class if filter
    filtered_members = members
    if class_filter:
        try:
            class_obj = ClassGroup.objects.get(id=class_filter)
            filtered_members = class_obj.members.filter(status='ACTIVE') if hasattr(class_obj, 'members') else members
        except ClassGroup.DoesNotExist:
            pass

    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        class_id = request.POST.get('class_id')
        att_date = request.POST.get('date', str(datetime.date.today()))
        present_member_ids = request.POST.getlist('present_members')
        remarks = request.POST.get('remarks', '').strip()

        if not class_id or not att_date:
            messages.error(request, "Class and date are required.")
            return redirect('attendance:class_attendance')

        class_group = get_object_or_404(ClassGroup, id=class_id)

        try:
            att_date_obj = datetime.datetime.strptime(att_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('attendance:class_attendance')

        with transaction.atomic():
            if action == 'edit':
                record_id = request.POST.get('record_id')
                record = get_object_or_404(ClassAttendanceRecord, id=record_id)
                record.class_group = class_group
                record.date = att_date_obj
                record.remarks = remarks
                record.save()
                if present_member_ids:
                    record.present_members.set(present_member_ids)
            else:
                # Check if record already exists for this class+date
                if ClassAttendanceRecord.objects.filter(class_group=class_group, date=att_date_obj).exists():
                    messages.error(request, f"Attendance already recorded for {class_group.name} on {att_date}.")
                    return redirect('attendance:class_attendance')

                record = ClassAttendanceRecord.objects.create(
                    class_group=class_group,
                    date=att_date_obj,
                    remarks=remarks,
                    recorded_by=request.user,
                )
                if present_member_ids:
                    record.present_members.set(present_member_ids)

            AuditLog.objects.create(
                user=request.user,
                action=f"Recorded class attendance for {class_group.name}",
                model_name="ClassAttendanceRecord",
                object_id=str(record.id),
                details=f"Date: {att_date}, Present: {len(present_member_ids)}",
            )

        messages.success(request, f"Class attendance for '{class_group.name}' recorded for {att_date} – {len(present_member_ids)} present.")
        return redirect('attendance:overview')

    context = {
        "active_nav": "attendance",
        "classes": classes,
        "members": members,
        "filtered_members": filtered_members,
        "records": records_page,
        "records_page": records_page,
        "paginator": paginator,
        "q": q,
        "class_filter": class_filter,
        "date_filter": date_filter,
        "total_records": total_records,
        "avg_present": round(avg_present, 1),
        "filtered_count": records_qs.count(),
        "today": datetime.date.today().isoformat(),
    }
    return render(request, "attendance/class_att.html", context)


@login_required(login_url='accounts:login')
def org_attendance_view(request):
    organisations = Organisation.objects.all().order_by('name')
    records_qs = OrganisationAttendanceRecord.objects.select_related('organisation', 'recorded_by').all()

    q = request.GET.get('q', '').strip()
    org_filter = request.GET.get('org_filter', '').strip()
    date_filter = request.GET.get('date', '').strip()

    if q:
        records_qs = records_qs.filter(
            models.Q(organisation__name__icontains=q) | models.Q(remarks__icontains=q)
        )

    if org_filter:
        records_qs = records_qs.filter(organisation_id=org_filter)

    if date_filter:
        try:
            filter_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            records_qs = records_qs.filter(date=filter_date)
        except ValueError:
            pass

    # Stats
    total_records = OrganisationAttendanceRecord.objects.count()
    total_attendees = OrganisationAttendanceRecord.objects.aggregate(total=Sum('attendees_count'))['total'] or 0

    paginator = Paginator(records_qs.order_by('-date', '-created_at'), 15)
    page_number = request.GET.get('page')
    records_page = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        org_id = request.POST.get('org_id')
        att_date = request.POST.get('date', str(datetime.date.today()))
        attendees_count = request.POST.get('attendees_count', '0')
        male_count = request.POST.get('male_count', '0')
        female_count = request.POST.get('female_count', '0')
        remarks = request.POST.get('remarks', '').strip()

        if not org_id or not att_date:
            messages.error(request, "Organisation and date are required.")
            return redirect('attendance:org_attendance')

        try:
            attendees_count = int(attendees_count)
            male_count = int(male_count)
            female_count = int(female_count)
            if attendees_count < 0 or male_count < 0 or female_count < 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Counts must be non-negative integers.")
            return redirect('attendance:org_attendance')

        org = get_object_or_404(Organisation, id=org_id)

        try:
            att_date_obj = datetime.datetime.strptime(att_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('attendance:org_attendance')

        with transaction.atomic():
            if action == 'edit':
                record_id = request.POST.get('record_id')
                record = get_object_or_404(OrganisationAttendanceRecord, id=record_id)
                record.organisation = org
                record.date = att_date_obj
                record.attendees_count = attendees_count
                record.male_count = male_count
                record.female_count = female_count
                record.remarks = remarks
                record.save()
            else:
                record = OrganisationAttendanceRecord.objects.create(
                    organisation=org,
                    date=att_date_obj,
                    attendees_count=attendees_count,
                    male_count=male_count,
                    female_count=female_count,
                    remarks=remarks,
                    recorded_by=request.user,
                )

            AuditLog.objects.create(
                user=request.user,
                action=f"Recorded org attendance for {org.name}",
                model_name="OrganisationAttendanceRecord",
                object_id=str(record.id),
                details=f"Date: {att_date}, Count: {attendees_count}",
            )

        messages.success(request, f"Organisation attendance of {attendees_count} recorded for '{org.name}'.")
        return redirect('attendance:overview')

    context = {
        "active_nav": "attendance",
        "organisations": organisations,
        "records": records_page,
        "records_page": records_page,
        "paginator": paginator,
        "q": q,
        "org_filter": org_filter,
        "date_filter": date_filter,
        "total_records": total_records,
        "total_attendees": total_attendees,
        "filtered_count": records_qs.count(),
        "today": datetime.date.today().isoformat(),
    }
    return render(request, "attendance/org_attendance.html", context)


@login_required(login_url='accounts:login')
def absentee_report_view(request):
    today = timezone.now().date()
    week_ago = today - datetime.timedelta(days=7)

    absentees_qs = Member.objects.filter(status='ACTIVE')
    followups_qs = AbsenteeFollowUp.objects.select_related('member', 'followed_up_by').all()

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_filter = request.GET.get('date', '').strip()

    if q:
        absentees_qs = absentees_qs.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q) | models.Q(phone_number__icontains=q)
        )
        followups_qs = followups_qs.filter(
            models.Q(member__first_name__icontains=q) | models.Q(member__last_name__icontains=q)
        )

    if status_filter:
        followups_qs = followups_qs.filter(follow_up_status=status_filter)

    if date_filter:
        try:
            filter_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            followups_qs = followups_qs.filter(absence_date=filter_date)
        except ValueError:
            pass

    # For demo: members with no recent attendance are absentees
    # Here we use members who have no class attendance in last 7 days
    recent_present_ids = ClassAttendanceRecord.objects.filter(date__gte=week_ago).values_list('present_members__id', flat=True)
    absentees = absentees_qs.exclude(id__in=recent_present_ids).order_by('first_name')[:100]

    # Stats
    total_absentees = absentees_qs.exclude(id__in=recent_present_ids).count()
    pending_followups = AbsenteeFollowUp.objects.filter(follow_up_status='PENDING').count()
    contacted = AbsenteeFollowUp.objects.filter(follow_up_status='CONTACTED').count()

    paginator = Paginator(followups_qs.order_by('-absence_date', '-created_at'), 15)
    page_number = request.GET.get('page')
    followups_page = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action', 'create_followup')

        if action == 'create_followup':
            member_id = request.POST.get('member_id')
            absence_date = request.POST.get('absence_date', str(today))
            reason = request.POST.get('reason', '').strip()
            follow_up_status = request.POST.get('follow_up_status', 'PENDING')
            notes = request.POST.get('follow_up_notes', '').strip()

            if not member_id or not absence_date:
                messages.error(request, "Member and absence date are required.")
                return redirect('attendance:absentee_report')

            member_obj = get_object_or_404(Member, id=member_id)

            try:
                absence_date_obj = datetime.datetime.strptime(absence_date, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Invalid date format.")
                return redirect('attendance:absentee_report')

            with transaction.atomic():
                followup, created = AbsenteeFollowUp.objects.update_or_create(
                    member=member_obj,
                    absence_date=absence_date_obj,
                    defaults={
                        'reason': reason,
                        'follow_up_status': follow_up_status,
                        'follow_up_notes': notes,
                        'followed_up_by': request.user,
                        'followed_up_at': timezone.now() if follow_up_status != 'PENDING' else None,
                    }
                )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"{'Created' if created else 'Updated'} absentee follow-up for {member_obj.get_full_name()}",
                    model_name="AbsenteeFollowUp",
                    object_id=str(followup.id),
                    details=f"Date: {absence_date}, Status: {follow_up_status}",
                )

            messages.success(request, f"Follow-up for {member_obj.get_full_name()} saved.")
            return redirect('attendance:absentee_report')

        elif action == 'update_followup':
            followup_id = request.POST.get('followup_id')
            new_status = request.POST.get('follow_up_status')
            notes = request.POST.get('follow_up_notes', '').strip()

            followup = get_object_or_404(AbsenteeFollowUp, id=followup_id)
            followup.follow_up_status = new_status
            followup.follow_up_notes = notes
            followup.followed_up_by = request.user
            followup.followed_up_at = timezone.now()
            followup.save()

            messages.success(request, f"Follow-up for {followup.member.get_full_name()} updated to {followup.get_follow_up_status_display()}.")
            return redirect('attendance:absentee_report')

    context = {
        "active_nav": "attendance",
        "absentees": absentees,
        "followups": followups_page,
        "followups_page": followups_page,
        "paginator": paginator,
        "q": q,
        "status_filter": status_filter,
        "date_filter": date_filter,
        "total_absentees": total_absentees,
        "pending_followups": pending_followups,
        "contacted": contacted,
        "status_choices": AbsenteeFollowUp.STATUS_CHOICES,
        "today": today.isoformat(),
        "week_ago": week_ago.isoformat(),
    }
    return render(request, "attendance/abstee_report.html", context)