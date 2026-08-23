from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.core.paginator import Paginator
from django.utils import timezone
from core.models import AuditLog
from .models import Organisation, OrganisationDues, OrganisationMembership, OrganisationMeeting
from members.models import Member
from attendance.models import OrganisationAttendanceRecord
import datetime


@login_required(login_url='accounts:login')
def org_list_view(request):
    organisations_qs = Organisation.objects.select_related('president', 'secretary', 'treasurer').all()

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    active_filter = request.GET.get('active', '').strip()

    if q:
        organisations_qs = organisations_qs.filter(
            models.Q(name__icontains=q)
            | models.Q(description__icontains=q)
            | models.Q(meeting_schedule__icontains=q)
            | models.Q(location__icontains=q)
        )

    if category:
        organisations_qs = organisations_qs.filter(category=category)

    if active_filter == 'active':
        organisations_qs = organisations_qs.filter(is_active=True)
    elif active_filter == 'inactive':
        organisations_qs = organisations_qs.filter(is_active=False)

    # Stats
    total_orgs = Organisation.objects.count()
    active_orgs = Organisation.objects.filter(is_active=True).count()
    total_members = Member.objects.filter(status='ACTIVE').count()
    total_dues = OrganisationDues.objects.aggregate(total=models.Sum('amount'))['total'] or 0

    paginator = Paginator(organisations_qs.order_by('name'), 12)
    page_number = request.GET.get('page')
    orgs_page = paginator.get_page(page_number)

    context = {
        "active_nav": "organisations",
        "organisations": orgs_page,
        "organisations_page": orgs_page,
        "paginator": paginator,
        "q": q,
        "category_filter": category,
        "active_filter": active_filter,
        "total_orgs": total_orgs,
        "active_orgs": active_orgs,
        "total_members": total_members,
        "total_dues": total_dues,
        "category_choices": Organisation.CATEGORY_CHOICES,
        "filtered_count": organisations_qs.count(),
    }
    return render(request, "organisations/e1org_list.html", context)


@login_required(login_url='accounts:login')
def org_details_view(request):
    org_id = request.GET.get('id')
    if org_id:
        org = get_object_or_404(Organisation, id=org_id)
    else:
        org = Organisation.objects.select_related('president', 'secretary', 'treasurer').first()
        if not org:
            messages.info(request, "No organisations found. Create one first.")
            return redirect('organisations:add_edit_org')

    dues_qs = OrganisationDues.objects.filter(organisation=org).select_related('member', 'recorded_by').order_by('-date_paid')
    memberships_qs = OrganisationMembership.objects.filter(organisation=org).select_related('member').order_by('-joined_date')
    meetings_qs = org.meetings.all().order_by('-date')[:10]
    attendance_qs = OrganisationAttendanceRecord.objects.filter(organisation=org).order_by('-date')[:10]

    q = request.GET.get('q', '').strip()
    if q:
        dues_qs = dues_qs.filter(
            models.Q(member_name__icontains=q) | models.Q(receipt_number__icontains=q)
        )
        memberships_qs = memberships_qs.filter(
            models.Q(member__first_name__icontains=q) | models.Q(member__last_name__icontains=q)
        )

    # Stats
    member_count = memberships_qs.count()
    total_dues = dues_qs.aggregate(total=models.Sum('amount'))['total'] or 0
    avg_attendance = 0
    if attendance_qs.exists():
        avg_attendance = sum(r.attendees_count for r in attendance_qs) / len(attendance_qs)

    paginator = Paginator(dues_qs, 15)
    page_number = request.GET.get('page')
    dues_page = paginator.get_page(page_number)

    context = {
        "active_nav": "organisations",
        "organisation": org,
        "org": org,
        "dues": dues_page,
        "dues_page": dues_page,
        "memberships": memberships_qs[:20],
        "meetings": meetings_qs,
        "attendances": attendance_qs,
        "member_count": member_count,
        "total_dues": total_dues,
        "avg_attendance": round(avg_attendance, 1),
        "q": q,
        "paginator": paginator,
    }
    return render(request, "organisations/e2org_details.html", context)


@login_required(login_url='accounts:login')
def add_edit_org_view(request):
    edit_id = request.GET.get('edit') or request.GET.get('id')
    edit_obj = None
    if edit_id:
        edit_obj = get_object_or_404(Organisation, id=edit_id)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.filter(profile__role__in=['ORGANISATION_LEADER', 'ADMIN']).select_related('profile').order_by('username')

    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'FELLOWSHIP')
        location = request.POST.get('location', '').strip()
        schedule = request.POST.get('meeting_schedule', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        president_id = request.POST.get('president')
        secretary_id = request.POST.get('secretary')
        treasurer_id = request.POST.get('treasurer')

        if not name:
            messages.error(request, "Organisation name is required.")
            return redirect('organisations:add_edit_org')

        with transaction.atomic():
            if action == 'edit' and edit_obj:
                old_name = edit_obj.name
                edit_obj.name = name
                edit_obj.description = description
                edit_obj.category = category
                edit_obj.location = location
                edit_obj.meeting_schedule = schedule
                edit_obj.is_active = is_active
                edit_obj.president_id = president_id if president_id else None
                edit_obj.secretary_id = secretary_id if secretary_id else None
                edit_obj.treasurer_id = treasurer_id if treasurer_id else None
                edit_obj.save()

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Updated organisation {edit_obj.id}",
                    model_name="Organisation",
                    object_id=str(edit_obj.id),
                    details=f"{old_name} -> {name}",
                )
                messages.success(request, f"Organisation '{name}' updated successfully.")
                return redirect('organisations:org_list')
            else:
                if Organisation.objects.filter(name=name).exists():
                    messages.error(request, f"Organisation with name '{name}' already exists.")
                    return redirect('organisations:add_edit_org')

                new_org = Organisation.objects.create(
                    name=name,
                    description=description,
                    category=category,
                    location=location,
                    meeting_schedule=schedule,
                    is_active=is_active,
                    president_id=president_id if president_id else None,
                    secretary_id=secretary_id if secretary_id else None,
                    treasurer_id=treasurer_id if treasurer_id else None,
                )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Created organisation {new_org.id}",
                    model_name="Organisation",
                    object_id=str(new_org.id),
                    details=f"Name: {name}, Category: {category}",
                )
                messages.success(request, f"Organisation '{name}' added successfully.")
                return redirect('organisations:org_list')

    context = {
        "active_nav": "organisations",
        "edit_obj": edit_obj,
        "edit_org": edit_obj,
        "organisation": edit_obj,
        "users": users,
        "category_choices": Organisation.CATEGORY_CHOICES,
    }
    return render(request, "organisations/e3add_org_edit.html", context)


@login_required(login_url='accounts:login')
def dues_contribution_view(request):
    organisations = Organisation.objects.filter(is_active=True).order_by('name')
    dues_qs = OrganisationDues.objects.select_related('organisation', 'member', 'recorded_by').all()

    q = request.GET.get('q', '').strip()
    org_filter = request.GET.get('org_filter', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if q:
        dues_qs = dues_qs.filter(
            models.Q(member_name__icontains=q)
            | models.Q(organisation__name__icontains=q)
            | models.Q(receipt_number__icontains=q)
        )

    if org_filter:
        dues_qs = dues_qs.filter(organisation_id=org_filter)

    if date_from:
        try:
            from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            dues_qs = dues_qs.filter(date_paid__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            dues_qs = dues_qs.filter(date_paid__lte=to_date)
        except ValueError:
            pass

    # Stats
    total_dues = dues_qs.aggregate(total=models.Sum('amount'))['total'] or 0
    total_records = dues_qs.count()
    by_org = dues_qs.values('organisation__name').annotate(total=models.Sum('amount')).order_by('-total')[:5]

    paginator = Paginator(dues_qs.order_by('-date_paid'), 20)
    page_number = request.GET.get('page')
    dues_page = paginator.get_page(page_number)

    members = Member.objects.filter(status='ACTIVE').order_by('first_name')[:200]

    if request.method == 'POST':
        action = request.POST.get('action', 'create')
        org_id = request.POST.get('org_id')
        member_id = request.POST.get('member_id')
        member_name = request.POST.get('member_name', '').strip()
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'CASH')
        date_paid = request.POST.get('date_paid')
        receipt_number = request.POST.get('receipt_number', '').strip()
        remarks = request.POST.get('remarks', '').strip()

        if not org_id or not amount or not date_paid:
            messages.error(request, "Organisation, amount and date paid are required.")
            return redirect('organisations:dues_contribution')

        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Amount must be a positive number.")
            return redirect('organisations:dues_contribution')

        org = get_object_or_404(Organisation, id=org_id)

        # Resolve member name
        member_obj = None
        if member_id:
            member_obj = get_object_or_404(Member, id=member_id)
            member_name = member_obj.get_full_name()
        elif not member_name:
            messages.error(request, "Member name or member selection is required.")
            return redirect('organisations:dues_contribution')

        with transaction.atomic():
            dues = OrganisationDues.objects.create(
                organisation=org,
                member=member_obj,
                member_name=member_name,
                amount=amount_val,
                payment_method=payment_method,
                date_paid=date_paid,
                receipt_number=receipt_number,
                remarks=remarks,
                recorded_by=request.user,
            )

            AuditLog.objects.create(
                user=request.user,
                action=f"Recorded dues for {org.name}",
                model_name="OrganisationDues",
                object_id=str(dues.id),
                details=f"Member: {member_name}, Amount: {amount_val}, Date: {date_paid}",
            )

        messages.success(request, f"Dues contribution of GHS {amount_val} for {member_name} recorded.")
        return redirect('organisations:org_list')

    context = {
        "active_nav": "organisations",
        "organisations": organisations,
        "dues": dues_page,
        "dues_page": dues_page,
        "paginator": paginator,
        "members": members,
        "q": q,
        "org_filter": org_filter,
        "date_from": date_from,
        "date_to": date_to,
        "total_dues": total_dues,
        "total_records": total_records,
        "by_org": by_org,
        "filtered_count": dues_qs.count(),
        "payment_method_choices": OrganisationDues.PAYMENT_METHOD_CHOICES,
        "today": datetime.date.today().isoformat(),
    }
    return render(request, "organisations/e5dues_contribution.html", context)


@login_required(login_url='accounts:login')
def org_attendance_view(request):
    organisations = Organisation.objects.filter(is_active=True).order_by('name')
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
    total_attendees = OrganisationAttendanceRecord.objects.aggregate(total=models.Sum('attendees_count'))['total'] or 0

    paginator = Paginator(records_qs.order_by('-date'), 15)
    page_number = request.GET.get('page')
    records_page = paginator.get_page(page_number)

    if request.method == 'POST':
        org_id = request.POST.get('org_id')
        att_date = request.POST.get('date', str(datetime.date.today()))
        attendees_count = request.POST.get('attendees_count', '0')
        male_count = request.POST.get('male_count', '0')
        female_count = request.POST.get('female_count', '0')
        remarks = request.POST.get('remarks', '').strip()

        if not org_id or not att_date:
            messages.error(request, "Organisation and date are required.")
            return redirect('organisations:org_attendance')

        try:
            attendees_count = int(attendees_count)
            male_count = int(male_count)
            female_count = int(female_count)
            if attendees_count < 0 or male_count < 0 or female_count < 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Counts must be non-negative integers.")
            return redirect('organisations:org_attendance')

        org = get_object_or_404(Organisation, id=org_id)

        try:
            att_date_obj = datetime.datetime.strptime(att_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('organisations:org_attendance')

        with transaction.atomic():
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
        return redirect('attendance:org_attendance')

    context = {
        "active_nav": "organisations",
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
    return render(request, "organisations/org_attendance.html", context)