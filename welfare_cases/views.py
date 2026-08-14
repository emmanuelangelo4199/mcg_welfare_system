from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.decorators import role_required
from .models import WelfareCase, VisitationLog, WelfareDisbursement
from members.models import Member

@login_required(login_url='accounts:login')
def welfare_cases_list_view(request):
    cases = WelfareCase.objects.select_related('member').all()
    return render(request, "welfare_cases/welfare_cases_list.html", {
        "active_nav": "welfare_cases",
        "cases": cases
    })

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
                status='SUBMITTED'
            )
            messages.success(request, f"Welfare case '{title}' submitted successfully!")
            return redirect('welfare_cases:welfare_cases_list')
        else:
            messages.error(request, "Please register a member before filing a case.")

    members = Member.objects.all()
    return render(request, "welfare_cases/new_welfare_case.html", {
        "active_nav": "welfare_cases",
        "members": members
    })

@login_required(login_url='accounts:login')
def welfare_case_details_view(request):
    case_id = request.GET.get('id')
    wcase = get_object_or_404(WelfareCase, id=case_id) if case_id else WelfareCase.objects.first()
    return render(request, "welfare_cases/welfare_case_details.html", {
        "active_nav": "welfare_cases",
        "wcase": wcase
    })

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
                visit_date=visit_date,
                visitors=visitors,
                findings=findings,
                recommendation=recommendation
            )
            messages.success(request, "Visit record saved successfully.")
            return redirect('welfare_cases:welfare_cases_list')

    cases = WelfareCase.objects.all()
    return render(request, "welfare_cases/visit_record_form.html", {
        "active_nav": "welfare_cases",
        "cases": cases
    })

@role_required(allowed_roles=['ADMIN', 'TREASURER', 'WELFARE_OFFICER'])
def welfare_payment_view(request):
    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        amount = request.POST.get('amount')
        date = request.POST.get('disbursement_date')
        payment_method = request.POST.get('payment_method', 'Mobile Money')
        ref_no = request.POST.get('reference_number', '').strip()

        wcase = get_object_or_404(WelfareCase, id=case_id) if case_id else WelfareCase.objects.first()
        if wcase:
            WelfareDisbursement.objects.update_or_create(
                welfare_case=wcase,
                defaults={
                    'amount': amount,
                    'disbursement_date': date,
                    'payment_method': payment_method,
                    'reference_number': ref_no
                }
            )
            wcase.status = 'DISBURSED'
            wcase.approved_amount = amount
            wcase.save()
            messages.success(request, f"Disbursement of GHS {amount} recorded for Case #{wcase.id}")
            return redirect('welfare_cases:welfare_cases_list')

    cases = WelfareCase.objects.filter(status__in=['APPROVED', 'SUBMITTED', 'UNDER_REVIEW'])
    return render(request, "welfare_cases/welfare_payment.html", {
        "active_nav": "welfare_cases",
        "cases": cases
    })

@role_required(allowed_roles=['ADMIN', 'WELFARE_OFFICER'])
def welfare_closure_view(request):
    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        wcase = get_object_or_404(WelfareCase, id=case_id) if case_id else WelfareCase.objects.first()
        if wcase:
            wcase.status = 'CLOSED'
            wcase.save()
            messages.success(request, f"Welfare Case #{wcase.id} has been closed.")
            return redirect('welfare_cases:welfare_cases_list')

    cases = WelfareCase.objects.exclude(status='CLOSED')
    return render(request, "welfare_cases/closure.html", {
        "active_nav": "welfare_cases",
        "cases": cases
    })
