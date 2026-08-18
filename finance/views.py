from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Max, Q
from django.utils import timezone
from core.decorators import role_required
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
    if request.method == 'POST':
        category = request.POST.get('category', 'TITHE')
        amount = request.POST.get('amount')
        date = request.POST.get('date')
        remarks = request.POST.get('remarks', '').strip()

        IncomeLedger.objects.create(
            category=category,
            amount=amount,
            date=date,
            recorded_by=request.user,
            remarks=remarks
        )
        messages.success(request, f"Income entry of GHS {amount} recorded.")
        return redirect('finance:income_ledger')

    return render(request, "finance/income/record_income.html", {"active_nav": "finance"})

@login_required(login_url='accounts:login')
def income_ledger_view(request):
    # Base queryset
    qs = IncomeLedger.objects.select_related('recorded_by').all()

    # --- Filters from GET ---
    q = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()
    date_from = (request.GET.get('date_from') or '').strip()
    date_to = (request.GET.get('date_to') or '').strip()

    # Text search: source / remarks / category / officer
    if q:
        qs = qs.filter(
            Q(remarks__icontains=q)
            | Q(category__icontains=q)
            | Q(recorded_by__username__icontains=q)
            | Q(recorded_by__first_name__icontains=q)
            | Q(recorded_by__last_name__icontains=q)
        )

    # Category filter — only apply if it is a valid choice
    valid_categories = {k for k, _ in IncomeLedger.CATEGORY_CHOICES}
    if category and category != 'ALL' and category in valid_categories:
        qs = qs.filter(category=category)

    # Date range filter (inclusive)
    if date_from:
        try:
            qs = qs.filter(date__gte=date_from)
        except Exception:
            pass
    if date_to:
        try:
            qs = qs.filter(date__lte=date_to)
        except Exception:
            pass

    qs = qs.order_by('-date', '-created_at')

    # --- Summary strip (filtered, before pagination) ---
    aggregates = qs.aggregate(total=Sum('amount'), largest=Max('amount'), count=Count('id'))
    total_income = aggregates['total'] or Decimal('0.00')
    largest_deposit = aggregates['largest'] or Decimal('0.00')
    record_count = aggregates['count'] or 0
    average_transaction = (total_income / record_count) if record_count else Decimal('0.00')

    # --- Pagination (25 per page) ---
    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Page subtotal (sum of amounts on current page)
    page_subtotal = sum((row.amount for row in page_obj.object_list), Decimal('0.00'))

    # Preserve querystring without `page` for pagination links
    querydict = request.GET.copy()
    querydict.pop('page', None)
    querystring = querydict.urlencode()

    return render(request, "finance/income/income_ledger.html", {
        "active_nav": "finance",
        "page_obj": page_obj,
        "incomes": page_obj.object_list,
        "total_income": total_income,
        "record_count": record_count,
        "average_transaction": average_transaction,
        "largest_deposit": largest_deposit,
        "page_subtotal": page_subtotal,
        "category_choices": IncomeLedger.CATEGORY_CHOICES,
        "selected_category": category or 'ALL',
        "q": q,
        "date_from": date_from,
        "date_to": date_to,
        "querystring": querystring,
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
