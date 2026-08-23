from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.core.paginator import Paginator
from django.utils import timezone
from core.models import AuditLog
from .models import ClassGroup, ClassMeeting
from members.models import Member
from attendance.models import ClassAttendanceRecord
import datetime


@login_required(login_url='accounts:login')
def class_list_view(request):
    classes_qs = ClassGroup.objects.select_related('leader', 'assistant_leader').all()

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    active_filter = request.GET.get('active', '').strip()

    if q:
        classes_qs = classes_qs.filter(
            models.Q(name__icontains=q)
            | models.Q(description__icontains=q)
            | models.Q(meeting_time__icontains=q)
            | models.Q(location__icontains=q)
        )

    if category:
        classes_qs = classes_qs.filter(category=category)

    if active_filter == 'active':
        classes_qs = classes_qs.filter(is_active=True)
    elif active_filter == 'inactive':
        classes_qs = classes_qs.filter(is_active=False)

    # Stats
    total_classes = ClassGroup.objects.count()
    active_classes = ClassGroup.objects.filter(is_active=True).count()
    total_members = Member.objects.filter(status='ACTIVE').count()
    # Average occupancy
    avg_occupancy = 0
    if classes_qs.exists():
        total_capacity = sum(c.capacity for c in classes_qs)
        total_count = sum(c.member_count for c in classes_qs)
        avg_occupancy = (total_count / total_capacity * 100) if total_capacity else 0

    paginator = Paginator(classes_qs.order_by('name'), 12)
    page_number = request.GET.get('page')
    classes_page = paginator.get_page(page_number)

    context = {
        "active_nav": "classes",
        "classes": classes_page,
        "classes_page": classes_page,
        "paginator": paginator,
        "q": q,
        "category_filter": category,
        "active_filter": active_filter,
        "total_classes": total_classes,
        "active_classes": active_classes,
        "total_members": total_members,
        "avg_occupancy": round(avg_occupancy, 1),
        "category_choices": ClassGroup.CATEGORY_CHOICES,
        "filtered_count": classes_qs.count(),
    }
    return render(request, "classes/d1class_list.html", context)


@login_required(login_url='accounts:login')
def class_detail_view(request):
    class_id = request.GET.get('id')
    if class_id:
        class_group = get_object_or_404(ClassGroup, id=class_id)
    else:
        class_group = ClassGroup.objects.select_related('leader', 'assistant_leader').first()
        if not class_group:
            messages.info(request, "No classes found. Create one first.")
            return redirect('classes:add_edit_class')

    members_qs = Member.objects.filter(assigned_class=class_group).select_related('assigned_class')
    q = request.GET.get('q', '').strip()

    if q:
        members_qs = members_qs.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q) | models.Q(phone_number__icontains=q)
        )

    # Stats
    members_count = members_qs.count()
    active_count = members_qs.filter(status='ACTIVE').count()
    recent_meetings = class_group.meetings.all().order_by('-date')[:5]
    recent_attendance = ClassAttendanceRecord.objects.filter(class_group=class_group).order_by('-date')[:5]

    paginator = Paginator(members_qs.order_by('first_name', 'last_name'), 20)
    page_number = request.GET.get('page')
    members_page = paginator.get_page(page_number)

    context = {
        "active_nav": "classes",
        "class_group": class_group,
        "members": members_page,
        "members_page": members_page,
        "paginator": paginator,
        "members_count": members_count,
        "active_count": active_count,
        "recent_meetings": recent_meetings,
        "recent_attendance": recent_attendance,
        "q": q,
    }
    return render(request, "classes/d2class_detail.html", context)


@login_required(login_url='accounts:login')
def add_edit_class_view(request):
    edit_id = request.GET.get('edit') or request.GET.get('id')
    edit_obj = None
    if edit_id:
        edit_obj = get_object_or_404(ClassGroup, id=edit_id)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    leaders = User.objects.filter(profile__role__in=['CLASS_LEADER', 'ADMIN', 'CATECHIST']).select_related('profile').order_by('username')

    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'BIBLE_STUDY')
        location = request.POST.get('location', '').strip()
        meeting_time = request.POST.get('meeting_time', '').strip()
        capacity = request.POST.get('capacity', '30')
        is_active = request.POST.get('is_active') == 'on'
        leader_id = request.POST.get('leader')
        assistant_leader_id = request.POST.get('assistant_leader')

        if not name:
            messages.error(request, "Class name is required.")
            return redirect('classes:add_edit_class')

        try:
            capacity = int(capacity)
            if capacity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Capacity must be a positive integer.")
            return redirect('classes:add_edit_class')

        with transaction.atomic():
            if action == 'edit' and edit_obj:
                old_name = edit_obj.name
                edit_obj.name = name
                edit_obj.description = description
                edit_obj.category = category
                edit_obj.location = location
                edit_obj.meeting_time = meeting_time
                edit_obj.capacity = capacity
                edit_obj.is_active = is_active
                edit_obj.leader_id = leader_id if leader_id else None
                edit_obj.assistant_leader_id = assistant_leader_id if assistant_leader_id else None
                edit_obj.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Updated class {edit_obj.id}",
                    model_name="ClassGroup",
                    object_id=str(edit_obj.id),
                    details=f"{old_name} -> {name}",
                )
                messages.success(request, f"Class '{name}' updated successfully.")
                return redirect('classes:class_list')
            else:
                if ClassGroup.objects.filter(name=name).exists():
                    messages.error(request, f"Class with name '{name}' already exists.")
                    return redirect('classes:add_edit_class')

                new_class = ClassGroup.objects.create(
                    name=name,
                    description=description,
                    category=category,
                    location=location,
                    meeting_time=meeting_time,
                    capacity=capacity,
                    is_active=is_active,
                    leader_id=leader_id if leader_id else None,
                    assistant_leader_id=assistant_leader_id if assistant_leader_id else None,
                )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Created class {new_class.id}",
                    model_name="ClassGroup",
                    object_id=str(new_class.id),
                    details=f"Name: {name}, Category: {category}",
                )
                messages.success(request, f"Class '{name}' created successfully.")
                return redirect('classes:class_list')

    context = {
        "active_nav": "classes",
        "edit_service": edit_obj,  # keep compatibility with template that might use edit_service
        "edit_obj": edit_obj,
        "edit_class": edit_obj,
        "leaders": leaders,
        "category_choices": ClassGroup.CATEGORY_CHOICES,
    }
    return render(request, "classes/d3add_edit_classForm.html", context)


@login_required(login_url='accounts:login')
def class_attendance_record_view(request):
    classes = ClassGroup.objects.filter(is_active=True).order_by('name')
    selected_class_id = request.GET.get('class_id') or request.GET.get('id')
    selected_class = None
    if selected_class_id:
        selected_class = get_object_or_404(ClassGroup, id=selected_class_id)
    else:
        selected_class = classes.first()

    members_qs = Member.objects.filter(status='ACTIVE')
    if selected_class:
        # Prefer members assigned to this class, but show all active as fallback
        assigned = members_qs.filter(assigned_class=selected_class)
        if assigned.exists():
            members_qs = assigned
    members_qs = members_qs.order_by('first_name', 'last_name')

    q = request.GET.get('q', '').strip()
    if q:
        members_qs = members_qs.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q) | models.Q(phone_number__icontains=q)
        )

    recent_records = ClassAttendanceRecord.objects.filter(class_group=selected_class).order_by('-date')[:10] if selected_class else []

    if request.method == 'POST':
        action = request.POST.get('action', 'record')
        class_id = request.POST.get('class_id')
        att_date = request.POST.get('date', str(datetime.date.today()))
        present_ids = request.POST.getlist('present_members')
        remarks = request.POST.get('remarks', '').strip()

        if not class_id or not att_date:
            messages.error(request, "Class and date are required.")
            return redirect('classes:class_attendance_record')

        class_group = get_object_or_404(ClassGroup, id=class_id)

        try:
            att_date_obj = datetime.datetime.strptime(att_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('classes:class_attendance_record')

        with transaction.atomic():
            if ClassAttendanceRecord.objects.filter(class_group=class_group, date=att_date_obj).exists():
                messages.error(request, f"Attendance already recorded for {class_group.name} on {att_date}.")
                return redirect('classes:class_attendance_record')

            record = ClassAttendanceRecord.objects.create(
                class_group=class_group,
                date=att_date_obj,
                remarks=remarks,
                recorded_by=request.user,
            )
            if present_ids:
                record.present_members.set(present_ids)

            AuditLog.objects.create(
                user=request.user,
                action=f"Recorded class attendance for {class_group.name}",
                model_name="ClassAttendanceRecord",
                object_id=str(record.id),
                details=f"Date: {att_date}, Present: {len(present_ids)}",
            )

        messages.success(request, f"Attendance recorded for {class_group.name} on {att_date} – {len(present_ids)} present.")
        return redirect('classes:class_attendance_report')

    paginator = Paginator(members_qs, 25)
    page_number = request.GET.get('page')
    members_page = paginator.get_page(page_number)

    context = {
        "active_nav": "classes",
        "classes": classes,
        "selected_class": selected_class,
        "members": members_page,
        "members_page": members_page,
        "paginator": paginator,
        "recent_records": recent_records,
        "q": q,
        "today": datetime.date.today().isoformat(),
        "class_id": selected_class_id,
    }
    return render(request, "classes/d4class_attendance_record.html", context)


@login_required(login_url='accounts:login')
def class_attendance_report_view(request):
    classes = ClassGroup.objects.filter(is_active=True).order_by('name')
    records_qs = ClassAttendanceRecord.objects.select_related('class_group', 'recorded_by').all()

    q = request.GET.get('q', '').strip()
    class_filter = request.GET.get('class_filter', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if q:
        records_qs = records_qs.filter(
            models.Q(class_group__name__icontains=q) | models.Q(remarks__icontains=q)
        )

    if class_filter:
        records_qs = records_qs.filter(class_group_id=class_filter)

    if date_from:
        try:
            from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            records_qs = records_qs.filter(date__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            records_qs = records_qs.filter(date__lte=to_date)
        except ValueError:
            pass

    # Stats
    total_records = records_qs.count()
    avg_rate = 0
    if records_qs.exists():
        rates = [r.attendance_rate for r in records_qs[:50]]
        avg_rate = sum(rates) / len(rates) if rates else 0

    # Group by class for summary
    from collections import defaultdict
    class_summary = defaultdict(list)
    for rec in records_qs.order_by('-date')[:100]:
        class_summary[rec.class_group.name].append(rec)

    summary_list = []
    for class_name, recs in class_summary.items():
        avg = sum(r.attendance_rate for r in recs) / len(recs) if recs else 0
        summary_list.append({
            'name': class_name,
            'count': len(recs),
            'avg_rate': avg,
            'last_date': recs[0].date if recs else None,
        })
    summary_list = sorted(summary_list, key=lambda x: x['avg_rate'], reverse=True)

    paginator = Paginator(records_qs.order_by('-date'), 20)
    page_number = request.GET.get('page')
    records_page = paginator.get_page(page_number)

    context = {
        "active_nav": "classes",
        "classes": classes,
        "records": records_page,
        "records_page": records_page,
        "paginator": paginator,
        "q": q,
        "class_filter": class_filter,
        "date_from": date_from,
        "date_to": date_to,
        "total_records": total_records,
        "avg_rate": round(avg_rate, 1),
        "summary_list": summary_list,
        "filtered_count": records_qs.count(),
    }
    return render(request, "classes/d5class_att_report.html", context)