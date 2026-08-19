from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib import messages
from datetime import timedelta
from django.core.paginator import Paginator
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from core.decorators import role_required
from core.models import AuditLog
from django.utils import timezone
from .models import Member, MemberRegularisation, MembershipStatusChange
from classes.models import ClassGroup
from attendance.models import ClassAttendanceRecord
from welfare_cases.models import WelfareCase
from organisations.models import Organisation


# Statuses a member can be moved to from this screen. PENDING is the initial
# state assigned at registration and is managed via the pending approval page.
STATUS_CHANGE_CHOICES = [
    (value, label) for value, label in Member.STATUS_CHOICES if value != 'PENDING'
]

@login_required(login_url='accounts:login')
def member_directory_view(request):
    search_query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    class_id = request.GET.get('class', '')
    gender = request.GET.get('gender', '')

    members = Member.objects.select_related('assigned_class').order_by('first_name', 'last_name')

    if search_query:
        members = members.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(phone_number__icontains=search_query)
            | Q(email__icontains=search_query)
        )
    if status in dict(Member.STATUS_CHOICES):
        members = members.filter(status=status)
    if class_id.isdigit():
        members = members.filter(assigned_class_id=int(class_id))
    if gender in dict(Member.GENDER_CHOICES):
        members = members.filter(gender=gender)

    paginator = Paginator(members, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Keep active filters when paging.
    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    context = {
        "active_nav": "members",
        "members": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "total_count": paginator.count,
        "querystring": querystring,
        "classes": ClassGroup.objects.order_by('name'),
        "status_choices": Member.STATUS_CHOICES,
        "gender_choices": Member.GENDER_CHOICES,
        "search_query": search_query,
        "filters": {"status": status, "class": class_id, "gender": gender},
    }
    return render(request, "members/c1member_directory.html", context)

@login_required(login_url='accounts:login')
def member_registration_view(request):
    """Register a member while preserving entered values when validation fails."""
    fields = (
        'first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth',
        'marital_status', 'occupation', 'hometown', 'phone_number', 'email',
        'residential_address', 'membership_type', 'date_of_baptism',
        'assigned_class', 'emergency_contact_name',
        'emergency_contact_relationship', 'emergency_contact_phone',
    )
    initial_form_data = {
        'first_name': '', 'middle_name': '', 'last_name': '', 'gender': '',
        'date_of_birth': '', 'marital_status': '', 'occupation': '',
        'hometown': '', 'phone_number': '', 'email': '',
        'residential_address': '', 'membership_type': 'FULL',
        'date_of_baptism': '', 'assigned_class': '',
        'emergency_contact_name': '', 'emergency_contact_relationship': '',
        'emergency_contact_phone': '',
    }

    def render_registration(form_data=None, errors=None, selected_organisation_ids=None):
        return render(request, "members/c2member_registration.html", {
            'active_nav': 'members',
            'classes': ClassGroup.objects.order_by('name'),
            'organisations': Organisation.objects.order_by('name'),
            'form_data': form_data or initial_form_data,
            'errors': errors or {},
            'selected_organisation_ids': selected_organisation_ids or [],
            'gender_choices': Member.GENDER_CHOICES,
            'marital_status_choices': Member.MARITAL_STATUS_CHOICES,
            'membership_type_choices': Member.MEMBERSHIP_TYPE_CHOICES,
        })

    if request.method != 'POST':
        return render_registration()

    form_data = {field: request.POST.get(field, '').strip() for field in fields}
    selected_organisation_ids = request.POST.getlist('organisations')
    errors = {}

    required_fields = {
        'first_name': 'Enter the member’s first name.',
        'last_name': 'Enter the member’s last name.',
        'gender': 'Select the member’s gender.',
        'date_of_birth': 'Enter the member’s date of birth.',
        'phone_number': 'Enter a primary phone number.',
        'residential_address': 'Enter a residential address.',
        'assigned_class': 'Select a Bible class.',
        'emergency_contact_name': 'Enter an emergency contact name.',
        'emergency_contact_relationship': 'Enter the contact’s relationship to the member.',
        'emergency_contact_phone': 'Enter an emergency contact phone number.',
    }
    for field, message in required_fields.items():
        if not form_data[field]:
            errors[field] = message

    if form_data['gender'] not in dict(Member.GENDER_CHOICES):
        errors['gender'] = 'Select either Male or Female.'
    if form_data['marital_status'] and form_data['marital_status'] not in dict(Member.MARITAL_STATUS_CHOICES):
        errors['marital_status'] = 'Select a valid marital status.'
    if form_data['membership_type'] not in dict(Member.MEMBERSHIP_TYPE_CHOICES):
        errors['membership_type'] = 'Select a valid membership type.'

    date_of_birth = parse_date(form_data['date_of_birth']) if form_data['date_of_birth'] else None
    if form_data['date_of_birth'] and date_of_birth is None:
        errors['date_of_birth'] = 'Enter a valid date of birth.'
    date_of_baptism = parse_date(form_data['date_of_baptism']) if form_data['date_of_baptism'] else None
    if form_data['date_of_baptism'] and date_of_baptism is None:
        errors['date_of_baptism'] = 'Enter a valid baptism date.'

    if form_data['email']:
        try:
            validate_email(form_data['email'])
        except ValidationError:
            errors['email'] = 'Enter a valid email address.'

    assigned_class = None
    if form_data['assigned_class']:
        assigned_class = ClassGroup.objects.filter(id=form_data['assigned_class']).first()
        if assigned_class is None:
            errors['assigned_class'] = 'Select a valid Bible class.'

    # Validate submitted organisation ids against the database. Always
    # initialise valid_organisation_ids (even when nothing was selected) so it
    # is safe to use further down no matter which branch runs.
    valid_organisation_ids = list(
        Organisation.objects.filter(id__in=selected_organisation_ids)
        .values_list('id', flat=True)
    )
    if len(valid_organisation_ids) != len(set(selected_organisation_ids)):
        errors['organisations'] = 'One or more selected organisations are unavailable.'

    uploaded_photo = request.FILES.get('passport_photo')
    if uploaded_photo:
        allowed_image_types = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
        if uploaded_photo.content_type not in allowed_image_types:
            errors['passport_photo'] = 'Upload a PNG, JPG, GIF, or WebP image.'
        elif uploaded_photo.size > 5 * 1024 * 1024:
            errors['passport_photo'] = 'The passport photo must be 5 MB or smaller.'

    if errors:
        return render_registration(form_data, errors, selected_organisation_ids)

    member = Member(
        first_name=form_data['first_name'],
        middle_name=form_data['middle_name'] or None,
        last_name=form_data['last_name'],
        gender=form_data['gender'],
        date_of_birth=date_of_birth,
        marital_status=form_data['marital_status'] or None,
        occupation=form_data['occupation'] or None,
        hometown=form_data['hometown'] or None,
        phone_number=form_data['phone_number'],
        email=form_data['email'] or None,
        residential_address=form_data['residential_address'],
        assigned_class=assigned_class,
        membership_type=form_data['membership_type'],
        date_of_baptism=date_of_baptism,
        status='PENDING',
        emergency_contact_name=form_data['emergency_contact_name'],
        emergency_contact_relationship=form_data['emergency_contact_relationship'],
        emergency_contact_phone=form_data['emergency_contact_phone'],
        passport_photo=uploaded_photo,
    )

    try:
        member.full_clean(exclude=['organisations', 'user'])
    except ValidationError as error:
        for field, messages_for_field in error.message_dict.items():
            errors[field] = messages_for_field[0]
        return render_registration(form_data, errors, selected_organisation_ids)

    member.save()
    member.organisations.set(valid_organisation_ids)
    messages.success(request, f"{member.get_full_name()} has been registered and is awaiting approval.")
    return redirect('members:member_directory')

@login_required(login_url='accounts:login')
def member_profile_view(request):
    """Render a member profile with the records that can be tied to a member."""
    member_id = request.GET.get('id')
    members = Member.objects.select_related('assigned_class')

    # Resolve the profile in priority order:
    # 1. The signed-in user's own linked member record (an ?id= for a
    #    different member is ignored so members cannot browse each other).
    # 2. An explicit ?id= request, for users without their own record
    #    (e.g. leaders opening a profile from the directory).
    # 3. A member whose email uniquely matches the account email: link the
    #    record to the account so future visits resolve directly.
    # 4. No record at all: render the empty profile state instead of
    #    defaulting to the first member in the database.
    member = members.filter(user=request.user).first()
    if member is None and member_id:
        if not member_id.isdigit():
            raise Http404("Member profile not found.")
        member = get_object_or_404(members, id=member_id)
    elif member is None and request.user.email:
        email_matches = list(members.filter(email__iexact=request.user.email)[:2])
        if len(email_matches) == 1:
            member = email_matches[0]
            member.user = request.user
            member.save()

    # The attendance model is class based. Build a clear twelve-week series
    # instead of implying that service or organisation attendance is available
    # at individual-member level.
    today = timezone.localdate()
    current_week_start = today - timedelta(days=today.weekday())
    week_starts = [current_week_start - timedelta(weeks=offset) for offset in range(11, -1, -1)]
    attendance_weeks = [
        {
            'start': week_start,
            'short_label': week_start.strftime('%d %b'),
            'label': week_start.strftime('%d %B %Y'),
        }
        for week_start in week_starts
    ]
    attendance_by_week = {}

    if member and member.assigned_class:
        records = (
            ClassAttendanceRecord.objects.filter(
                class_group=member.assigned_class,
                date__gte=week_starts[0],
                date__lte=current_week_start + timedelta(days=6),
            )
            .prefetch_related('present_members')
            .order_by('date')
        )
        for record in records:
            record_week_start = record.date - timedelta(days=record.date.weekday())
            # A class can have more than one record in a week. The most recent
            # record is the best representation for this compact overview.
            attendance_by_week[record_week_start] = record

    class_attendance_cells = []
    for week_start in week_starts:
        record = attendance_by_week.get(week_start)
        if record is None:
            class_attendance_cells.append({'state': 'na', 'label': 'No record', 'date': None})
            continue
 
        is_present = any(attendee.id == member.id for attendee in record.present_members.all())
        class_attendance_cells.append({
            'state': 'present' if is_present else 'absent',
            'label': 'Present' if is_present else 'Absent',
            'date': record.date,
        })

    attendance_record_count = len(attendance_by_week)
    attendance_present_count = sum(cell['state'] == 'present' for cell in class_attendance_cells)
    attendance_rate = round((attendance_present_count / attendance_record_count) * 100) if attendance_record_count else 0
 
    welfare_cases = []
    profile_history = []
    if member:
        welfare_cases = list(
            WelfareCase.objects.filter(member=member)
            .order_by('-updated_at')[:5]
        )
        profile_history = [
            {
                'date': member.updated_at,
                'title': 'Profile last updated',
                'description': 'Member contact, status, or class information was updated in the membership register.',
            },
            {
                'date': member.created_at,
                'title': 'Member registered',
                'description': 'The member profile was created in the society management system.',
            },
        ]
        profile_history.extend(
            {
                'date': welfare_case.created_at,
                'title': 'Welfare case opened',
                'description': f'{welfare_case.get_case_type_display()}: {welfare_case.title}',
            }
            for welfare_case in welfare_cases
        )
        profile_history.sort(key=lambda event: event['date'], reverse=True)

    status_changes = (
        list(member.status_changes.select_related('recorded_by')[:10]) if member else []
    )

    return render(request, "members/c3member_profile.html", {
        "active_nav": "members",
        "member": member,
        "attendance_weeks": attendance_weeks,
        "class_attendance_cells": class_attendance_cells,
        "attendance_record_count": attendance_record_count,
        "attendance_present_count": attendance_present_count,
        "attendance_rate": attendance_rate,
        "welfare_cases": welfare_cases,
        "profile_history": profile_history,
        "status_changes": status_changes,
    })

@login_required(login_url='accounts:login')
def edit_member_view(request):
    member_id = request.GET.get('id')
    member = get_object_or_404(Member, id=member_id) if member_id else Member.objects.first()

    if request.method == 'POST' and member:
        member.first_name = (request.POST.get('first_name') or member.first_name or '').strip()
        member.last_name = (request.POST.get('last_name') or member.last_name or '').strip()

        phone_number = request.POST.get('phone_number', member.phone_number or '')
        email = request.POST.get('email', member.email or '')
        member.phone_number = phone_number.strip() if phone_number else None
        member.email = email.strip() if email else None

        member.save()
        messages.success(request, f"Updated profile for {member.get_full_name()}")
        return redirect('members:member_directory')

    classes = ClassGroup.objects.all()
    return render(request, "members/c4edit_member.html", {
        "active_nav": "members",
        "member": member,
        "classes": classes
    })

@role_required(allowed_roles=['ADMIN', 'CLASS_LEADER'])
def pending_members_view(request):
    pending_members = Member.objects.filter(status='PENDING').select_related('assigned_class')
    return render(request, "members/c5pending_member_list.html", {
        "active_nav": "members",
        "pending_members": pending_members
    })

@login_required(login_url='accounts:login')
def member_regularisation_view(request):
    """Record a leaders' meeting decision for a pending member."""
    member_id = request.POST.get('member_id') or request.GET.get('id')
    pending_members = Member.objects.filter(status='PENDING').select_related('assigned_class').order_by(
        'first_name', 'last_name'
    )
    member = get_object_or_404(pending_members, id=member_id) if member_id else pending_members.first()
    classes = list(ClassGroup.objects.select_related('leader').order_by('name'))

    def class_options():
        options = []
        for class_group in classes:
            leader = class_group.leader
            leader_name = ''
            if leader:
                leader_name = leader.get_full_name().strip() or leader.username
            options.append({
                'id': class_group.id,
                'name': class_group.name,
                'leader_name': leader_name or 'Leader not assigned',
            })
        return options

    def render_regularisation(form_data=None, errors=None):
        defaults = {
            'meeting_reference': '',
            'approval_date': timezone.localdate().isoformat(),
            'decision': '',
            'assigned_class': str(member.assigned_class_id) if member and member.assigned_class_id else '',
            'remarks': '',
        }
        return render(request, "members/c6member_regularisation.html", {
            'active_nav': 'members',
            'member': member,
            'pending_members': pending_members,
            'class_options': class_options(),
            'form_data': form_data or defaults,
            'errors': errors or {},
            'member_number_preview': f"MCG-{member.id:05d}" if member else 'MCG-SMS-TBD',
        })

    if request.method != 'POST' or member is None:
        return render_regularisation()

    form_data = {
        'meeting_reference': request.POST.get('meeting_reference', '').strip(),
        'approval_date': request.POST.get('approval_date', '').strip(),
        'decision': request.POST.get('decision', '').strip(),
        'assigned_class': request.POST.get('assigned_class', '').strip(),
        'remarks': request.POST.get('remarks', '').strip(),
    }
    errors = {}
    if form_data['decision'] not in dict(MemberRegularisation.DECISION_CHOICES):
        errors['decision'] = 'Select the leaders’ meeting decision.'

    approval_date = parse_date(form_data['approval_date']) if form_data['approval_date'] else None
    if approval_date is None:
        errors['approval_date'] = 'Enter the approval date.'

    assigned_class = None
    if form_data['assigned_class']:
        assigned_class = ClassGroup.objects.filter(id=form_data['assigned_class']).first()
        if assigned_class is None:
            errors['assigned_class'] = 'Select a valid society class.'

    if errors:
        return render_regularisation(form_data, errors)

    MemberRegularisation.objects.create(
        member=member,
        decision=form_data['decision'],
        meeting_reference=form_data['meeting_reference'] or None,
        approval_date=approval_date,
        assigned_class=assigned_class,
        remarks=form_data['remarks'] or None,
        processed_by=request.user,
    )

    if form_data['decision'] == 'APPROVED':
        member.status = 'REGULARIZED'
    elif form_data['decision'] == 'DECLINED':
        member.status = 'DECLINED'
    else:
        member.status = 'PENDING'
    if assigned_class:
        member.assigned_class = assigned_class
    member.save()

    messages.success(request, f"Regularisation decision recorded for {member.get_full_name()}.")
    return redirect('members:member_directory')

@login_required(login_url='accounts:login')
def member_transfer_view(request):
    return render(request, "members/c7member_transfer.html", {"active_nav": "members"})


def _search_members(query):
    """Return members matching a name, member ID, phone number or email."""
    lookup = (
        Q(first_name__icontains=query)
        | Q(middle_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(phone_number__icontains=query)
        | Q(email__icontains=query)
    )
    if query.isdigit():
        lookup |= Q(id=int(query))
    return (
        Member.objects.select_related('assigned_class')
        .filter(lookup)
        .order_by('first_name', 'last_name')
    )


@role_required(allowed_roles=['ADMIN'])
def status_management_view(request):
    query = request.GET.get('q', '').strip()
    member_id = request.GET.get('member', '').strip()

    search_results = []
    member = None
    errors = {}
    form_data = {
        'new_status': '',
        'effective_date': '',
        'reason': '',
        'authorised_by': '',
        'note_reference': '',
    }

    if query:
        search_results = list(_search_members(query)[:10])

    if request.method == 'POST':
        member_id = request.POST.get('member', '').strip()
        form_data = {field: request.POST.get(field, '').strip() for field in form_data}

        member = (
            Member.objects.select_related('assigned_class').filter(id=member_id).first()
            if member_id.isdigit()
            else None
        )

        if member is None:
            errors['member'] = 'Select a member before updating their status.'
        else:
            new_status = form_data['new_status']
            if new_status not in dict(STATUS_CHANGE_CHOICES):
                errors['new_status'] = 'Select a valid new status.'
            elif member.status == new_status:
                errors['new_status'] = (
                    f'{member.get_full_name()} is already marked as '
                    f'{member.get_status_display().lower()}.'
                )

            effective_date = parse_date(form_data['effective_date']) if form_data['effective_date'] else None
            if effective_date is None:
                errors['effective_date'] = 'Enter a valid effective date.'

            if len(form_data['reason']) < 10:
                errors['reason'] = 'Provide a detailed reason (at least 10 characters).'

            if form_data['authorised_by'] not in dict(MembershipStatusChange.AUTHORISED_BY_CHOICES):
                errors['authorised_by'] = 'Select the authorising officer.'

            if not errors:
                previous_status = member.status
                member.status = new_status
                member.save()

                MembershipStatusChange.objects.create(
                    member=member,
                    previous_status=previous_status,
                    new_status=new_status,
                    effective_date=effective_date,
                    reason=form_data['reason'],
                    authorised_by=form_data['authorised_by'],
                    note_reference=form_data['note_reference'],
                    recorded_by=request.user,
                )
                AuditLog.objects.create(
                    user=request.user,
                    action=f'Updated membership status for {member.get_full_name()}',
                    model_name='Member',
                    object_id=str(member.id),
                    details=(
                        f'{dict(Member.STATUS_CHOICES)[previous_status]} -> '
                        f'{dict(Member.STATUS_CHOICES)[new_status]}; '
                        f'effective {effective_date}; authorised by '
                        f'{dict(MembershipStatusChange.AUTHORISED_BY_CHOICES)[form_data["authorised_by"]]}; '
                        f'reason: {form_data["reason"]}'
                    ),
                )
                messages.success(
                    request,
                    f"{member.get_full_name()}'s status updated to "
                    f'{member.get_status_display()}.'
                )
                return redirect(f"{reverse('members:status_management')}?member={member.id}")

    elif member_id.isdigit():
        member = Member.objects.select_related('assigned_class').filter(id=member_id).first()

    status_history = (
        member.status_changes.select_related('recorded_by')[:5] if member else []
    )

    return render(request, "members/c8status_management.html", {
        "active_nav": "members",
        "query": query,
        "search_results": search_results,
        "member": member,
        "errors": errors,
        "form_data": form_data,
        "status_choices": STATUS_CHANGE_CHOICES,
        "authorised_by_choices": MembershipStatusChange.AUTHORISED_BY_CHOICES,
        "status_history": status_history,
    })