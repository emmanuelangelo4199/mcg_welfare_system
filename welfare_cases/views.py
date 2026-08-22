from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import role_required
from .models import VisitationLog, WelfareCase, WelfareDisbursement
from members.models import Member


@login_required(login_url='accounts:login')
def welfare_cases_list_view(request):
    cases = WelfareCase.objects.select_related('member', 'assigned_officer').all()

    query = request.GET.get('q', '').strip()
    if query:
        cases = cases.filter(
            Q(member__first_name__icontains=query)
            | Q(member__last_name__icontains=query)
            | Q(title__icontains=query)
            | Q(case_type__icontains=query)
        )

    month_start = timezone.localdate().replace(day=1)
    context = {
        "active_nav": "welfare_cases",
        "cases": cases,
        "query": query,
        "active_count": WelfareCase.objects.exclude(status__in=['CLOSED', 'REJECTED']).count(),
        "new_this_month_count": WelfareCase.objects.filter(created_at__date__gte=month_start).count(),
        "pending_support_count": WelfareCase.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        "resolved_count": WelfareCase.objects.filter(status='CLOSED').count(),
        "total_count": WelfareCase.objects.count(),
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

        member = get_object_or_404(Member, id=member_id) if member_id else Member.objects.first()
        if member:
            wcase = WelfareCase.objects.create(
                member=member,
                case_type=case_type,
                title=title,
                description=description,
                requested_amount=requested_amount,
                status='SUBMITTED',
                assigned_officer=request.user if request.user.is_staff else None,
            )
            messages.success(request, f"Welfare case '{title}' submitted successfully!")
            return redirect('welfare_cases:welfare_case_details')
        else:
            messages.error(request, "Please register a member before filing a case.")

    members = Member.objects.filter(status__in=['ACTIVE', 'REGULARIZED']).order_by('first_name', 'last_name')
    return render(request, "welfare_cases/new_welfare_case.html", {
        "active_nav": "welfare_cases",
        "members": members,
    })


@login_required(login_url='accounts:login')
def welfare_case_details_view(request):
    case_id = request.GET.get('id')
    wcase = get_object_or_404(WelfareCase, id=case_id) if case_id else WelfareCase.objects.first()
    if wcase is None:
        messages.info(request, "No welfare cases have been opened yet.")
        return redirect('welfare_cases:welfare_cases_list')

    visitations = wcase.visitations.order_by('-visit_date')
    disbursement = WelfareDisbursement.objects.filter(welfare_case=wcase).first()

    context = {
        "active_nav": "welfare_cases",
        "wcase": wcase,
        "visitations": visitations,
        "disbursement": disbursement,
    }
    return render(request, "welfare_cases/welfare_case_details.html", context)


@login_required(login_url='accounts:login')
def visit_record_form_view(request):
    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        visit_date = request.POST.get('visit_date')
        visitors = request.POST.get('visitors', '').strip()
        findings = request.POST.get('findings', '').strip()
        recommendation = request.POST.get('recommendation', '').strip()

        wcase = get_object_or_404(WelfareCase, id=case_id) if case_id else WelfareCase.objects.first()
        if wcase:
            VisitationLog.objects.create(
                welfare_case=wcase,
                visit_date=visit_date or timezone.localdate(),
                visitors=visitors,
                findings=findings,
                recommendation=recommendation,
            )
            messages.success(request, "Visit record saved successfully.")
            return redirect('welfare_cases:welfare_cases_list')

    cases = WelfareCase.objects.all()
    selected_case = None
    case_id = request.GET.get('case_id')
    if case_id:
        selected_case = WelfareCase.objects.filter(id=case_id).first()
    if selected_case is None:
        selected_case = cases.first()

    return render(request, "welfare_cases/visit_record_form.html", {
        "active_nav": "welfare_cases",
        "cases": cases,
        "selected_case": selected_case,
    })


@role_required(allowed_roles=['ADMIN', 'TREASURER', 'WELFARE_OFFICER'])
def welfare_payment_view(request):
    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        amount = request.POST.get('amount')
        disbursement_date = request.POST.get('disbursement_date')
        payment_method = request.POST.get('payment_method', 'Mobile Money')
        ref_no = request.POST.get('reference_number', '').strip()

        wcase = get_object_or_404(WelfareCase, id=case_id) if case_id else WelfareCase.objects.first()
        if wcase:
            WelfareDisbursement.objects.update_or_create(
                welfare_case=wcase,
                defaults={
                    'amount': amount,
                    'disbursement_date': disbursement_date or timezone.localdate(),
                    'payment_method': payment_method,
                    'reference_number': ref_no,
                },
            )
            wcase.status = 'DISBURSED'
            wcase.approved_amount = amount
            wcase.save(update_fields=['status', 'approved_amount'])
            messages.success(request, f"Disbursement of GHS {amount} recorded for Case #{wcase.id}.")
            return redirect('welfare_cases:welfare_cases_list')

    cases = WelfareCase.objects.filter(status__in=['APPROVED', 'SUBMITTED', 'UNDER_REVIEW'])
    selected_case = None
    case_id = request.GET.get('case_id')
    if case_id:
        selected_case = WelfareCase.objects.filter(id=case_id).first()
    if selected_case is None:
        selected_case = cases.first()

    disbursements = WelfareDisbursement.objects.select_related('welfare_case__member').order_by('-disbursement_date')
    total_disbursed = sum(d.amount for d in disbursements) or 0

    return render(request, "welfare_cases/welfare_payment.html", {
        "active_nav": "welfare_cases",
        "cases": cases,
        "selected_case": selected_case,
        "disbursements": disbursements[:10],
        "total_disbursed": total_disbursed,
    })


@role_required(allowed_roles=['ADMIN', 'WELFARE_OFFICER'])
def welfare_closure_view(request):
    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        wcase = get_object_or_404(WelfareCase, id=case_id) if case_id else WelfareCase.objects.first()
        if wcase:
            wcase.status = 'CLOSED'
            wcase.closure_outcome = request.POST.get('closure_outcome') or 'RESOLVED'
            wcase.closure_notes = request.POST.get('closure_notes', '').strip()
            closed_at_raw = request.POST.get('closed_at')
            try:
                wcase.closed_at = (
                    timezone.make_aware(timezone.datetime.fromisoformat(closed_at_raw))
                    if closed_at_raw else timezone.now()
                )
            except (ValueError, TypeError):
                wcase.closed_at = timezone.now()
            wcase.save(update_fields=['status', 'closure_outcome', 'closure_notes', 'closed_at'])
            messages.success(request, f"Welfare Case #{wcase.id} has been closed.")
            return redirect('welfare_cases:welfare_cases_list')

    cases = WelfareCase.objects.exclude(status='CLOSED')
    selected_case = None
    case_id = request.GET.get('case_id')
    if case_id:
        selected_case = WelfareCase.objects.filter(id=case_id).first()
    if selected_case is None:
        selected_case = cases.first()

    return render(request, "welfare_cases/closure.html", {
        "active_nav": "welfare_cases",
        "cases": cases,
        "selected_case": selected_case,
    })
