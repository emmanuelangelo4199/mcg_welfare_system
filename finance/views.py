from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from core.decorators import role_required
from services.models import ChurchService
from .models import EXPENSE_CATEGORY_CHOICES, IncomeLedger, ExpenseLedger, Budget


@login_required(login_url='accounts:login')
def finance_dashboard_view(request):
    total_income = IncomeLedger.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expense = ExpenseLedger.objects.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0
    net_balance = total_income - total_expense

    recent_incomes = IncomeLedger.objects.all().order_by('-date')[:5]
    recent_expenses = ExpenseLedger.objects.all().order_by('-date')[:5]

    return render(request, "finance/income/finance_dashboard.html", {
        "active_nav": "finance",
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "recent_incomes": recent_incomes,
        "recent_expenses": recent_expenses
    })

@role_required(allowed_roles=['ADMIN', 'TREASURER'])
def record_income_view(request):
    categories = dict(IncomeLedger.CATEGORY_CHOICES)
    methods = dict(IncomeLedger.PAYMENT_METHOD_CHOICES)

    if request.method == 'POST':
        category = request.POST.get('category', '').strip().upper()
        payment_method = request.POST.get('payment_method', '').strip().upper()
        amount = request.POST.get('amount', '').strip()
        date = request.POST.get('date', '').strip()
        service_id = request.POST.get('service', '')
        remarks = request.POST.get('remarks', '').strip()

        reference = request.POST.get('reference', '').strip()

        if category not in categories:
            category = 'OTHER'
        if payment_method not in methods:
            payment_method = 'CASH'
        # A reference number only means something for MoMo and cheques.
        if payment_method not in ('MOMO', 'CHEQUE'):
            reference = ''

        if not amount or not date:
            messages.error(request, "Transaction date and amount are required.")
            return render(request, "finance/income/record_income.html", {
                "active_nav": "finance",
                "category_choices": IncomeLedger.CATEGORY_CHOICES,
                "payment_methods": IncomeLedger.PAYMENT_METHOD_CHOICES,
                "services": ChurchService.objects.order_by('-service_date')[:50],
                "today": timezone.localdate(),
                "form_data": request.POST,
            })

        entry = IncomeLedger.objects.create(
            category=category,
            amount=amount,
            date=date,
            service=ChurchService.objects.filter(id=service_id).first() if service_id else None,
            payment_method=payment_method,
            reference=reference or None,
            recorded_by=request.user,
            remarks=remarks,
        )
        messages.success(
            request, f"{entry.get_category_display()} of GHS {entry.amount} recorded.")
        return redirect('finance:income_ledger')

    return render(request, "finance/income/record_income.html", {
        "active_nav": "finance",
        "category_choices": IncomeLedger.CATEGORY_CHOICES,
        "payment_methods": IncomeLedger.PAYMENT_METHOD_CHOICES,
        "services": ChurchService.objects.order_by('-service_date')[:50],
        "today": timezone.localdate(),
    })

@login_required(login_url='accounts:login')
def income_ledger_view(request):
    incomes = IncomeLedger.objects.select_related('recorded_by').all().order_by('-date')
    return render(request, "finance/income/income_ledger.html", {
        "active_nav": "finance",
        "incomes": incomes
    })

@role_required(allowed_roles=['ADMIN', 'TREASURER'])
def budget_manage_view(request):
    valid_categories = dict(EXPENSE_CATEGORY_CHOICES)
    if request.method == 'POST':
        year = request.POST.get('fiscal_year') or timezone.localdate().year
        category = request.POST.get('category', '').strip().upper()
        allocated = request.POST.get('allocated_amount')
        notes = request.POST.get('notes', '').strip()

        if category not in valid_categories:
            messages.error(request, "Please choose a valid budget category.")
            return redirect('finance:budget_manage')

        # One allocation per category per year: setting it again updates it,
        # so budget utilisation never double-counts.
        budget, created = Budget.objects.update_or_create(
            fiscal_year=year,
            category=category,
            defaults={'allocated_amount': allocated, 'notes': notes},
        )
        verb = "added" if created else "updated"
        messages.success(request, f"Budget entry for '{budget.get_category_display()}' {verb}.")
        return redirect('finance:budget_manage')

    budgets = Budget.objects.all().order_by('-fiscal_year', 'category')
    context = {
        "active_nav": "finance",
        "budgets": budgets,
        "category_choices": EXPENSE_CATEGORY_CHOICES,
        "current_year": timezone.localdate().year,
    }
    return render(request, "finance/income/budget_manage.html", context)

@role_required(allowed_roles=['ADMIN', 'TREASURER'])
def record_expense_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', '').strip()
        if category not in dict(EXPENSE_CATEGORY_CHOICES):
            category = 'OTHER' 
        amount = request.POST.get('amount')
        date = request.POST.get('date')
        description = request.POST.get('description', '').strip()

        ExpenseLedger.objects.create(
            title=title,
            category=category,
            amount=amount,
            date=date,
            recorded_by=request.user,
            description=description,
            status='PENDING'
        )
        messages.success(request, f"Expense voucher for '{title}' submitted for approval.")
        return redirect('finance:expense_ledger')

    context = {
        "active_nav": "finance",
        "category_choices": EXPENSE_CATEGORY_CHOICES,
    }
    return render(request, "finance/expense/record_expense.html", context)

@login_required(login_url='accounts:login')
def expense_ledger_view(request):
    expenses = ExpenseLedger.objects.select_related('recorded_by', 'approved_by').all().order_by('-date')
    return render(request, "finance/expense/expence_ledger.html", {
        "active_nav": "finance",
        "expenses": expenses
    })

@role_required(allowed_roles=['ADMIN', 'TREASURER'])
def expense_approve_view(request):
    if request.method == 'POST':
        expense_id = request.POST.get('expense_id')
        action = request.POST.get('action')  # 'approve' or 'reject'
        
        expense = get_object_or_404(ExpenseLedger, id=expense_id)
        if action == 'approve':
            expense.status = 'APPROVED'
            expense.approved_by = request.user
            messages.success(request, f"Expense '{expense.title}' approved.")
        elif action == 'reject':
            expense.status = 'REJECTED'
            messages.info(request, f"Expense '{expense.title}' rejected.")
        expense.save()
        return redirect('finance:expense_approve')

    pending_expenses = ExpenseLedger.objects.filter(status='PENDING').order_by('-date')
    return render(request, "finance/expense/expence_approve.html", {
        "active_nav": "finance",
        "pending_expenses": pending_expenses
    })

@login_required(login_url='accounts:login')
def cashbook_view(request):
    incomes = IncomeLedger.objects.all().order_by('-date')
    expenses = ExpenseLedger.objects.filter(status='APPROVED').order_by('-date')
    return render(request, "finance/report/cashbook_view.html", {
        "active_nav": "finance",
        "incomes": incomes,
        "expenses": expenses
    })

@login_required(login_url='accounts:login')
def receipt_payment_report_view(request):
    return render(request, "finance/report/recepit_pay.html", {"active_nav": "finance"})

@login_required(login_url='accounts:login')
def payment_tracker_view(request):
    return render(request, "finance/report/stat_payment_tracker.html", {"active_nav": "finance"})
