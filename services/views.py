from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.core.paginator import Paginator
from django.utils import timezone
from core.models import AuditLog
from .models import ChurchService, ServiceProgramItem, ServiceAttendance
from members.models import Member


@login_required(login_url='accounts:login')
def upcoming_events_view(request):
    services_qs = ChurchService.objects.all()

    q = request.GET.get('q', '').strip()
    service_type = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_filter = request.GET.get('date', '').strip()  # upcoming, past, today

    if q:
        services_qs = services_qs.filter(
            models.Q(title__icontains=q)
            | models.Q(theme__icontains=q)
            | models.Q(preacher__icontains=q)
            | models.Q(description__icontains=q)
        )

    if service_type:
        services_qs = services_qs.filter(service_type=service_type)

    if status_filter:
        services_qs = services_qs.filter(status=status_filter)

    today = timezone.now().date()
    if date_filter == 'upcoming':
        services_qs = services_qs.filter(service_date__gte=today, status='SCHEDULED')
    elif date_filter == 'past':
        services_qs = services_qs.filter(service_date__lt=today)
    elif date_filter == 'today':
        services_qs = services_qs.filter(service_date=today)

    # Stats
    total_services = ChurchService.objects.count()
    upcoming_count = ChurchService.objects.filter(service_date__gte=today, status='SCHEDULED').count()
    completed_count = ChurchService.objects.filter(status='COMPLETED').count()
    featured = ChurchService.objects.filter(is_featured=True, service_date__gte=today).order_by('service_date')[:3]

    paginator = Paginator(services_qs.order_by('service_date', 'start_time'), 12)
    page_number = request.GET.get('page')
    services_page = paginator.get_page(page_number)

    context = {
        "active_nav": "services",
        "services": services_page,
        "services_page": services_page,
        "paginator": paginator,
        "featured_services": featured,
        "q": q,
        "type_filter": service_type,
        "status_filter": status_filter,
        "date_filter": date_filter,
        "total_services": total_services,
        "upcoming_count": upcoming_count,
        "completed_count": completed_count,
        "type_choices": ChurchService.SERVICE_TYPE_CHOICES,
        "status_choices": ChurchService.STATUS_CHOICES,
        "filtered_count": services_qs.count(),
    }
    return render(request, "services/f5upcomingevents.html", context)


@login_required(login_url='accounts:login')
def event_calendar_view(request):
    services = ChurchService.objects.all().order_by('service_date', 'start_time')

    # For calendar, group by date
    from collections import defaultdict
    calendar_data = defaultdict(list)
    for svc in services:
        calendar_data[svc.service_date].append(svc)

    # Month filter
    month = request.GET.get('month')
    year = request.GET.get('year')
    today = timezone.now().date()

    try:
        if month and year:
            filter_month = int(month)
            filter_year = int(year)
        else:
            filter_month = today.month
            filter_year = today.year
    except ValueError:
        filter_month = today.month
        filter_year = today.year

    month_services = services.filter(service_date__month=filter_month, service_date__year=filter_year)

    # Stats
    total_month = month_services.count()
    by_type = month_services.values('service_type').annotate(count=models.Count('id'))

    context = {
        "active_nav": "services",
        "services": services,
        "calendar_data": dict(calendar_data),
        "month_services": month_services,
        "filter_month": filter_month,
        "filter_year": filter_year,
        "today": today,
        "total_month": total_month,
        "by_type": by_type,
        "type_choices": ChurchService.SERVICE_TYPE_CHOICES,
    }
    return render(request, "services/event_calendar.html", context)


@login_required(login_url='accounts:login')
def service_program_form_view(request):
    members = Member.objects.filter(status='ACTIVE').order_by('first_name')[:100]

    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        title = request.POST.get('title', '').strip()
        service_type = request.POST.get('service_type', 'SUNDAY')
        description = request.POST.get('description', '').strip()
        service_date = request.POST.get('service_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        location = request.POST.get('location', 'Main Auditorium').strip()
        theme = request.POST.get('theme', '').strip()
        preacher = request.POST.get('preacher', '').strip()
        liturgist = request.POST.get('liturgist', '').strip()
        status = request.POST.get('status', 'SCHEDULED')
        is_featured = request.POST.get('is_featured') == 'on'

        if not title or not service_date or not start_time:
            messages.error(request, "Title, service date and start time are required.")
            return redirect('services:service_program_form')

        with transaction.atomic():
            if action == 'edit':
                service_id = request.POST.get('service_id')
                service = get_object_or_404(ChurchService, id=service_id)
                service.title = title
                service.service_type = service_type
                service.description = description
                service.service_date = service_date
                service.start_time = start_time
                service.end_time = end_time if end_time else None
                service.location = location
                service.theme = theme
                service.preacher = preacher
                service.liturgist = liturgist
                service.status = status
                service.is_featured = is_featured
                service.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Updated service program {service.id}",
                    model_name="ChurchService",
                    object_id=str(service.id),
                    details=f"Title: {title}, Date: {service_date}",
                )
                messages.success(request, f"Service program '{title}' updated.")
            else:
                service = ChurchService.objects.create(
                    title=title,
                    service_type=service_type,
                    description=description,
                    service_date=service_date,
                    start_time=start_time,
                    end_time=end_time if end_time else None,
                    location=location,
                    theme=theme,
                    preacher=preacher,
                    liturgist=liturgist,
                    status=status,
                    is_featured=is_featured,
                    created_by=request.user,
                )

                # Handle program items if provided
                titles = request.POST.getlist('program_title')
                durations = request.POST.getlist('program_duration')
                responsibles = request.POST.getlist('program_responsible')
                for idx, prog_title in enumerate(titles):
                    if prog_title.strip():
                        ServiceProgramItem.objects.create(
                            service=service,
                            order=idx,
                            title=prog_title.strip(),
                            duration_minutes=int(durations[idx]) if idx < len(durations) and durations[idx].isdigit() else 5,
                            responsible_person=responsibles[idx].strip() if idx < len(responsibles) else '',
                        )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Created service program {service.id}",
                    model_name="ChurchService",
                    object_id=str(service.id),
                    details=f"Title: {title}, Date: {service_date}, Type: {service_type}",
                )
                messages.success(request, f"Service program '{title}' scheduled for {service_date}.")

            return redirect('services:upcoming_events')

    # For edit mode
    edit_id = request.GET.get('edit')
    edit_service = None
    if edit_id:
        edit_service = get_object_or_404(ChurchService, id=edit_id)

    context = {
        "active_nav": "services",
        "members": members,
        "edit_service": edit_service,
        "type_choices": ChurchService.SERVICE_TYPE_CHOICES,
        "status_choices": ChurchService.STATUS_CHOICES,
    }
    return render(request, "services/f2service_program_form.html", context)


@login_required(login_url='accounts:login')
def service_detail_view(request):
    service_id = request.GET.get('id')
    if service_id:
        service = get_object_or_404(ChurchService, id=service_id)
    else:
        service = ChurchService.objects.select_related('created_by').first()
        if not service:
            messages.info(request, "No services found. Create one first.")
            return redirect('services:service_program_form')

    program_items = service.program_items.all().order_by('order')
    attendances = service.attendances.select_related('member', 'recorded_by').all()
    attendance_count = attendances.filter(is_present=True).count()
    guest_count = attendances.filter(is_guest=True, is_present=True).count()

    # Related upcoming services
    related_services = ChurchService.objects.filter(service_date__gte=service.service_date).exclude(id=service.id).order_by('service_date')[:5]

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_status':
            new_status = request.POST.get('new_status')
            if new_status in dict(ChurchService.STATUS_CHOICES):
                old_status = service.status
                service.status = new_status
                service.save(update_fields=['status', 'updated_at'])

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Changed service {service.id} status",
                    model_name="ChurchService",
                    object_id=str(service.id),
                    details=f"{old_status} -> {new_status}",
                )
                messages.success(request, f"Status updated to {service.get_status_display()}.")
                return redirect(f"{request.path}?id={service.id}")

        elif action == 'toggle_featured':
            service.is_featured = not service.is_featured
            service.save(update_fields=['is_featured', 'updated_at'])
            messages.success(request, f"Service {'featured' if service.is_featured else 'unfeatured'}.")
            return redirect(f"{request.path}?id={service.id}")

    context = {
        "active_nav": "services",
        "service": service,
        "program_items": program_items,
        "attendances": attendances,
        "attendance_count": attendance_count,
        "guest_count": guest_count,
        "related_services": related_services,
        "status_choices": ChurchService.STATUS_CHOICES,
    }
    return render(request, "services/f3service_detail.html", context)


@login_required(login_url='accounts:login')
def service_attendance_view(request):
    service_id = request.GET.get('service_id') or request.GET.get('id')
    services = ChurchService.objects.all().order_by('-service_date')

    if service_id:
        selected_service = get_object_or_404(ChurchService, id=service_id)
    else:
        selected_service = services.first()

    members = Member.objects.filter(status='ACTIVE').order_by('first_name', 'last_name')
    q = request.GET.get('q', '').strip()

    if q:
        members = members.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q) | models.Q(phone_number__icontains=q)
        )

    attendances = []
    if selected_service:
        attendances = ServiceAttendance.objects.filter(service=selected_service).select_related('member')

    # Stats
    total_members = Member.objects.filter(status='ACTIVE').count()
    present_count = attendances.filter(is_present=True).count() if attendances else 0

    if request.method == 'POST':
        action = request.POST.get('action', 'record')

        if action == 'record' and selected_service:
            member_ids = request.POST.getlist('member_ids')
            guest_names = request.POST.getlist('guest_name')

            with transaction.atomic():
                # Clear existing for this service if bulk overwrite? For simplicity, update_or_create
                for member_id in member_ids:
                    if member_id:
                        member_obj = get_object_or_404(Member, id=member_id)
                        ServiceAttendance.objects.update_or_create(
                            service=selected_service,
                            member=member_obj,
                            defaults={
                                'is_present': True,
                                'is_guest': False,
                                'recorded_by': request.user,
                            }
                        )

                for guest_name in guest_names:
                    if guest_name.strip():
                        ServiceAttendance.objects.create(
                            service=selected_service,
                            guest_name=guest_name.strip(),
                            is_present=True,
                            is_guest=True,
                            recorded_by=request.user,
                        )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Recorded attendance for service {selected_service.id}",
                    model_name="ServiceAttendance",
                    object_id=str(selected_service.id),
                    details=f"Members: {len(member_ids)}, Guests: {len([g for g in guest_names if g.strip()])}",
                )

            messages.success(request, f"Attendance recorded for {selected_service.title} – {len(member_ids)} members.")
            return redirect(f"{request.path}?service_id={selected_service.id}")

        elif action == 'bulk_present' and selected_service:
            # Mark all filtered members as present
            with transaction.atomic():
                for m in members[:100]:
                    ServiceAttendance.objects.update_or_create(
                        service=selected_service,
                        member=m,
                        defaults={'is_present': True, 'is_guest': False, 'recorded_by': request.user}
                    )
            messages.success(request, f"All {members.count()} members marked present for {selected_service.title}.")
            return redirect(f"{request.path}?service_id={selected_service.id}")

    # Pagination for members
    paginator = Paginator(members, 20)
    page_number = request.GET.get('page')
    members_page = paginator.get_page(page_number)

    context = {
        "active_nav": "services",
        "services": services,
        "selected_service": selected_service,
        "members": members_page,
        "members_page": members_page,
        "paginator": paginator,
        "attendances": attendances,
        "q": q,
        "total_members": total_members,
        "present_count": present_count,
        "attendance_percentage": (present_count / total_members * 100) if total_members else 0,
    }
    return render(request, "services/f4serice_attendance.html", context)