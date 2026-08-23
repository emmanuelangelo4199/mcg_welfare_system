from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.core.paginator import Paginator
from django.utils import timezone
from core.decorators import role_required
from core.models import AuditLog
from .models import WelfareCase, VisitationLog, WelfareDisbursement, WelfareCaseActivity
from members.models import Member


@login_required(login_url='accounts:login')
def welfare_cases_list_view(request):
    cases_qs = WelfareCase.objects.select_related('member', 'assigned_officer').all()

    # Filters
    q = request.GET.get('q', '').strip()
    case_type = request.GET.get('case_type', '').strip()
    status = request.GET.get('status', '').strip()
    priority = request.GET.get('priority', '').strip()

    if q:
        cases_qs = cases_qs.filter(
            models.Q(title__icontains=q)
            | models.Q(description__icontains=q)
            | models.Q(member__first_name__icontains=q)
            | models.Q(member__last_name__icontains=q)
        )

    if case_type:
        cases_qs = cases_qs.filter(case_type=case_type)

    if status:
        cases_qs = cases_qs.filter(status=status)

    if priority:
        cases_qs = cases_qs.filter(priority=priority)

    # Stats
    total_cases = WelfareCase.objects.count()
    open_cases = WelfareCase.objects.exclude(status__in=['CLOSED', 'REJECTED']).count()
    pending_review = WelfareCase.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count()
    total_requested = WelfareCase.objects.aggregate(total=models.Sum('requested_amount'))['total'] or 0
    total_approved = WelfareCase.objects.aggregate(total=models.Sum('approved_amount'))['total'] or 0

    # Pagination
    paginator = Paginator(cases_qs.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    cases_page = paginator.get_page(page_number)

    context = {
        "active_nav": "welfare_cases",
        "cases": cases_page,
        "cases_page": cases_page,
        "paginator": paginator,
        "q": q,
        "case_type_filter": case_type,
        "status_filter": status,
        "priority_filter": priority,
        "total_cases": total_cases,
        "open_cases": open_cases,
        "pending_review": pending_review,
        "total_requested": total_requested,
        "total_approved": total_approved,
        "case_type_choices": WelfareCase.CASE_TYPE_CHOICES,
        "status_choices": WelfareCase.STATUS_CHOICES,
        "priority_choices": WelfareCase.PRIORITY_CHOICES,
        "filtered_count": cases_qs.count(),
    }
    return render(request, "welfare_cases/welfare_cases_list.html", context)


@login_required(login_url='accounts:login')
def new_welfare_case_view(request):
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        case_type = request.POST.get('case_type', 'HARDSHIP')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        requested_amount = request.POST.get('requested_amount', '0.00')
        priority = request.POST.get('priority', 'MEDIUM')
        is_confidential = request.POST.get('is_confidential') == 'on'
        assigned_officer_id = request.POST.get('assigned_officer')

        if not title or not description:
            messages.error(request, "Title and description are required.")
            return redirect('welfare_cases:new_welfare_case')

        try:
            requested_amount = float(requested_amount)
            if requested_amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Requested amount must be a positive number.")
            return redirect('welfare_cases:new_welfare_case')

        member = None
        if member_id:
            member = get_object_or_404(Member, id=member_id)
        else:
            member = Member.objects.first()

        if not member:
            messages.error(request, "Please register a member before filing a case.")
            return redirect('welfare_cases:new_welfare_case')

        with transaction.atomic():
            wcase = WelfareCase.objects.create(
                member=member,
                case_type=case_type,
                title=title,
                description=description,
                requested_amount=requested_amount,
                priority=priority,
                is_confidential=is_confidential,
                status='SUBMITTED',
                created_by=request.user,
                assigned_officer_id=assigned_officer_id if assigned_officer_id else None,
            )

            WelfareCaseActivity.objects.create(
                welfare_case=wcase,
                action='CREATED',
                description=f"Case created: {title} for {member.get_full_name()}",
                performed_by=request.user,
            )

            AuditLog.objects.create(
                user=request.user,
                action=f"Created welfare case {wcase.id}",
                model_name="WelfareCase",
                object_id=str(wcase.id),
                details=f"Member: {member.get_full_name()}, Type: {case_type}, Amount: {requested_amount}",
            )

        messages.success(request, f"Welfare case '{title}' submitted successfully!")
        return redirect('welfare_cases:welfare_cases_list')

    members = Member.objects.all().order_by('first_name', 'last_name')
    from django.contrib.auth import get_user_model
    User = get_user_model()
    officers = User.objects.filter(profile__role__in=['WELFARE_OFFICER', 'ADMIN', 'SOCIETY_MINISTER']).select_related('profile')

    return render(request, "welfare_cases/new_welfare_case.html", {
        "active_nav": "welfare_cases",
        "members": members,
        "officers": officers,
        "case_type_choices": WelfareCase.CASE_TYPE_CHOICES,
        "priority_choices": WelfareCase.PRIORITY_CHOICES,
    })


@login_required(login_url='accounts:login')
def welfare_case_details_view(request):
    case_id = request.GET.get('id')
    if case_id:
        wcase = get_object_or_404(WelfareCase, id=case_id)
    else:
        wcase = WelfareCase.objects.select_related('member', 'assigned_officer').first()
        if not wcase:
            messages.info(request, "No welfare cases found. Create one first.")
            return redirect('welfare_cases:new_welfare_case')

    # Handle status change POST
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'change_status':
            new_status = request.POST.get('new_status')
            review_notes = request.POST.get('review_notes', '').strip()

            if new_status and wcase.can_transition_to(new_status):
                old_status = wcase.status
                wcase.status = new_status
                if review_notes:
                    wcase.review_notes = review_notes
                if new_status == 'CLOSED':
                    wcase.closed_at = timezone.now()
                wcase.save()

                WelfareCaseActivity.objects.create(
                    welfare_case=wcase,
                    action='STATUS_CHANGED',
                    description=f"Status changed from {old_status} to {new_status}. Notes: {review_notes}",
                    performed_by=request.user,
                )

                AuditLog.objects.create(
                    user=request.user,
                    action=f"Changed welfare case {wcase.id} status",
                    model_name="WelfareCase",
                    object_id=str(wcase.id),
                    details=f"{old_status} -> {new_status}",
                )

                messages.success(request, f"Case status updated to {wcase.get_status_display()}.")
                return redirect(f"{request.path}?id={wcase.id}")
            else:
                messages.error(request, f"Cannot transition from {wcase.status} to {new_status}.")

        elif action == 'assign_officer':
            officer_id = request.POST.get('officer_id')
            if officer_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                officer = get_object_or_404(User, id=officer_id)
                wcase.assigned_officer = officer
                wcase.save(update_fields=['assigned_officer'])

                WelfareCaseActivity.objects.create(
                    welfare_case=wcase,
                    action='ASSIGNED',
                    description=f"Assigned to {officer.get_full_name() or officer.username}",
                    performed_by=request.user,
                )

                messages.success(request, f"Case assigned to {officer.get_full_name() or officer.username}.")
                return redirect(f"{request.path}?id={wcase.id}")

    visitations = wcase.visitations.select_related('created_by').all()
    disbursement = getattr(wcase, 'disbursement', None)
    activities = wcase.activities.select_related('performed_by').all()[:20]

    from django.contrib.auth import get_user_model
    User = get_user_model()
    officers = User.objects.filter(profile__role__in=['WELFARE_OFFICER', 'ADMIN']).select_related('profile')

    context = {
        "active_nav": "welfare_cases",
        "wcase": wcase,
        "visitations": visitations,
        "disbursement": disbursement,
        "activities": activities,
        "officers": officers,
        "status_choices": WelfareCase.STATUS_CHOICES,
    }
    return render(request, "welfare_cases/welfare_case_details.html", context)


@login_required(login_url='accounts:login')
def visit_record_form_view(request):
    cases = WelfareCase.objects.exclude(status__in=['CLOSED', 'REJECTED']).select_related('member').order_by('-created_at')

    preselected_case_id = request.GET.get('case_id')

    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        visit_date = request.POST.get('visit_date')
        visitors = request.POST.get('visitors', '').strip()
        findings = request.POST.get('findings', '').strip()
        recommendation = request.POST.get('recommendation', '').strip()

        if not case_id or not visit_date or not visitors or not findings:
            messages.error(request, "Case, visit date, visitors and findings are required.")
            return redirect('welfare_cases:visit_record_form')

        wcase = get_object_or_404(WelfareCase, id=case_id)

        with transaction.atomic():
            visit = VisitationLog.objects.create(
                welfare_case=wcase,
                visit_date=visit_date,
                visitors=visitors,
                findings=findings,
                recommendation=recommendation,
                created_by=request.user,
            )

            WelfareCaseActivity.objects.create(
                welfare_case=wcase,
                action='VISIT_LOGGED',
                description=f"Visitation logged on {visit_date} by {visitors}",
                performed_by=request.user,
            )

            AuditLog.objects.create(
                user=request.user,
                action=f"Logged visitation for case {wcase.id}",
                model_name="VisitationLog",
                object_id=str(visit.id),
                details=f"Date: {visit_date}, Visitors: {visitors}",
            )

        messages.success(request, "Visit record saved successfully.")
        return redirect(f"/welfare-cases/details/?id={wcase.id}")

    return render(request, "welfare_cases/visit_record_form.html", {
        "active_nav": "welfare_cases",
        "cases": cases,
        "preselected_case_id": preselected_case_id,
    })


@role_required(allowed_roles=['ADMIN', 'TREASURER', 'WELFARE_OFFICER'])
def welfare_payment_view(request):
    cases = WelfareCase.objects.filter(status__in=['APPROVED', 'SUBMITTED', 'UNDER_REVIEW']).select_related('member').order_by('-created_at')
    preselected_case_id = request.GET.get('case_id')

    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        amount = request.POST.get('amount')
        date = request.POST.get('disbursement_date')
        payment_method = request.POST.get('payment_method', 'MOBILE_MONEY')
        ref_no = request.POST.get('reference_number', '').strip()
        remarks = request.POST.get('remarks', '').strip()

        if not case_id or not amount or not date:
            messages.error(request, "Case, amount and disbursement date are required.")
            return redirect('welfare_cases:welfare_payment')

        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Amount must be a positive number.")
            return redirect('welfare_cases:welfare_payment')

        wcase = get_object_or_404(WelfareCase, id=case_id)

        with transaction.atomic():
            disbursement, created = WelfareDisbursement.objects.update_or_create(
                welfare_case=wcase,
                defaults={
                    'amount': amount_val,
                    'disbursement_date': date,
                    'payment_method': payment_method,
                    'reference_number': ref_no,
                    'remarks': remarks,
                    'created_by': request.user,
                }
            )

            old_status = wcase.status
            wcase.status = 'DISBURSED'
            wcase.approved_amount = amount_val
            wcase.save()

            WelfareCaseActivity.objects.create(
                welfare_case=wcase,
                action='DISBURSED',
                description=f"Disbursed GHS {amount_val} via {payment_method}. Ref: {ref_no}",
                performed_by=request.user,
            )

            AuditLog.objects.create(
                user=request.user,
                action=f"Recorded disbursement for case {wcase.id}",
                model_name="WelfareDisbursement",
                object_id=str(disbursement.id),
                details=f"Amount: {amount_val}, Method: {payment_method}, Status: {old_status} -> DISBURSED",
            )

        messages.success(request, f"Disbursement of GHS {amount_val} recorded for Case #{wcase.id}")
        return redirect('welfare_cases:welfare_cases_list')

    return render(request, "welfare_cases/welfare_payment.html", {
        "active_nav": "welfare_cases",
        "cases": cases,
        "preselected_case_id": preselected_case_id,
        "payment_method_choices": WelfareDisbursement.PAYMENT_METHOD_CHOICES,
    })


@role_required(allowed_roles=['ADMIN', 'WELFARE_OFFICER'])
def welfare_closure_view(request):
    cases = WelfareCase.objects.exclude(status='CLOSED').select_related('member').order_by('-created_at')
    preselected_case_id = request.GET.get('case_id')

    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        closure_notes = request.POST.get('closure_notes', '').strip()

        if not case_id:
            messages.error(request, "Case is required.")
            return redirect('welfare_cases:welfare_closure')

        wcase = get_object_or_404(WelfareCase, id=case_id)

        with transaction.atomic():
            wcase.status = 'CLOSED'
            wcase.closed_at = timezone.now()
            if closure_notes:
                wcase.review_notes = (wcase.review_notes + "\n\nClosure: " + closure_notes) if wcase.review_notes else closure_notes
            wcase.save()

            WelfareCaseActivity.objects.create(
                welfare_case=wcase,
                action='CLOSED',
                description=f"Case closed. Notes: {closure_notes}",
                performed_by=request.user,
            )

            AuditLog.objects.create(
                user=request.user,
                action=f"Closed welfare case {wcase.id}",
                model_name="WelfareCase",
                object_id=str(wcase.id),
                details=closure_notes,
            )

        messages.success(request, f"Welfare Case #{wcase.id} has been closed.")
        return redirect('welfare_cases:welfare_cases_list')

    return render(request, "welfare_cases/closure.html", {
        "active_nav": "welfare_cases",
        "cases": cases,
        "preselected_case_id": preselected_case_id,
    })