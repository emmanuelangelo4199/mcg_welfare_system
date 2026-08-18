from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from core.decorators import role_required
from services.models import ChurchService
from .models import EXPENSE_CATEGORY_CHOICES, IncomeLedger, ExpenseLedger, Budget
from datetime import date as _date
import calendar
from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Q, Max, Avg, Count



@login_required(login_url='accounts:login')
def finance_dashboard_view(request):
    today = timezone.localdate()

    # --- Month aggregates ---
    month_income = IncomeLedger.objects.filter(
        date__year=today.year, date__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    month_expense = ExpenseLedger.objects.filter(
        date__year=today.year, date__month=today.month,
        status__in=['APPROVED', 'PAID']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Previous month for delta %
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1

    prev_income = IncomeLedger.objects.filter(
        date__year=prev_year, date__month=prev_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    prev_expense = ExpenseLedger.objects.filter(
        date__year=prev_year, date__month=prev_month,
        status__in=['APPROVED', 'PAID']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    def pct_change(current, previous):
        if not previous or previous == 0:
            return None
        try:
            return round((float(current) - float(previous)) / float(previous) * 100, 1)
        except Exception:
            return None

    income_change = pct_change(month_income, prev_income)
    expense_change = pct_change(month_expense, prev_expense)

    total_income = IncomeLedger.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_expense = ExpenseLedger.objects.filter(status__in=['APPROVED', 'PAID']).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    net_balance = total_income - total_expense
    month_net = month_income - month_expense

    # Statutory due = sum of STATUTORY budgets for current fiscal year minus paid statutory expenses
    fiscal_year = today.year
    statutory_budget = Budget.objects.filter(
        fiscal_year=fiscal_year, category='STATUTORY'
    ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0.00')
    statutory_paid = ExpenseLedger.objects.filter(
        category='STATUTORY', status__in=['APPROVED', 'PAID'],
        date__year=fiscal_year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    statutory_due = statutory_budget - statutory_paid
    if statutory_due < 0:
        statutory_due = Decimal('0.00')
    # Fallback demo value if no budgets configured
    if statutory_budget == 0:
        statutory_due = Decimal('1500.00')

    # --- 6-month summary ---
    six_months = []
    max_month_total = Decimal('1')
    for i in range(5, -1, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        inc = IncomeLedger.objects.filter(date__year=y, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        exp = ExpenseLedger.objects.filter(date__year=y, date__month=m, status__in=['APPROVED', 'PAID']).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        six_months.append({
            'label': calendar.month_abbr[m],
            'income': inc,
            'expense': exp,
            'year': y,
            'month': m,
        })
        if inc > max_month_total:
            max_month_total = inc
        if exp > max_month_total:
            max_month_total = exp
    if max_month_total == 0:
        max_month_total = Decimal('1')
    for entry in six_months:
        entry['income_pct'] = int(float(entry['income']) / float(max_month_total) * 90) + 10 if entry['income'] else 8
        entry['expense_pct'] = int(float(entry['expense']) / float(max_month_total) * 90) + 10 if entry['expense'] else 8
        # clamp
        entry['income_pct'] = max(8, min(95, entry['income_pct']))
        entry['expense_pct'] = max(8, min(95, entry['expense_pct']))

    # --- Income breakdown (current month by category) ---
    from django.db.models import Sum as _Sum
    breakdown_qs = IncomeLedger.objects.filter(
        date__year=today.year, date__month=today.month
    ).values('category').annotate(total=_Sum('amount')).order_by('-total')
    breakdown_total = sum((r['total'] for r in breakdown_qs), Decimal('0.00')) or Decimal('0.00')
    breakdown = []
    breakdown_colors = {
        'TITHE': '#5c0219',
        'OFFERING': '#A3283F',
        'WELFARE': '#775a00',
        'HARVEST': '#C49A2B',
        'DONATION': '#fece5b',
        'OTHER': '#eec04f',
    }
    for row in breakdown_qs:
        cat = row['category']
        total = row['total']
        pct = round(float(total) / float(breakdown_total) * 100, 1) if breakdown_total else 0
        breakdown.append({
            'category': cat,
            'label': dict(IncomeLedger.CATEGORY_CHOICES).get(cat, cat),
            'total': total,
            'pct': pct,
            'color': breakdown_colors.get(cat, '#5c0219'),
        })
    # Fallback demo breakdown if no data
    if not breakdown:
        breakdown = [
            {'category': 'TITHE', 'label': 'Tithes', 'total': month_income * Decimal('0.45') if month_income else Decimal('5600'), 'pct': 45, 'color': '#5c0219'},
            {'category': 'HARVEST', 'label': 'Pledges', 'total': month_income * Decimal('0.25') if month_income else Decimal('3100'), 'pct': 25, 'color': '#A3283F'},
            {'category': 'WELFARE', 'label': 'Welfare', 'total': month_income * Decimal('0.20') if month_income else Decimal('2500'), 'pct': 20, 'color': '#775a00'},
            {'category': 'OTHER', 'label': 'Others', 'total': month_income * Decimal('0.10') if month_income else Decimal('1250'), 'pct': 10, 'color': '#fece5b'},
        ]
        breakdown_total = sum((b['total'] for b in breakdown), Decimal('0.00'))

    # --- Recent transactions (combined) ---
    recent_incomes = list(IncomeLedger.objects.select_related('recorded_by', 'service').order_by('-date', '-created_at')[:5])
    recent_expenses = list(ExpenseLedger.objects.select_related('recorded_by').order_by('-date', '-id')[:5])
    # Build unified recent list
    combined = []
    for inc in recent_incomes:
        combined.append({
            'ref': f'INC-{inc.id:05d}',
            'title': inc.get_category_display(),
            'subtitle': f'{inc.get_payment_method_display()} • {inc.date.strftime("%b %d, %Y")}',
            'amount': inc.amount,
            'is_income': True,
            'status': 'Completed',
            'status_class': 'bg-success/10 text-success',
            'date': inc.date,
        })
    for exp in recent_expenses:
        status_map = {
            'PENDING': ('Pending Approval', 'bg-warning/10 text-warning'),
            'APPROVED': ('Completed', 'bg-success/10 text-success'),
            'PAID': ('Completed', 'bg-success/10 text-success'),
            'REJECTED': ('Rejected', 'bg-error/10 text-error'),
        }
        label, css = status_map.get(exp.status, (exp.get_status_display(), 'bg-surface-variant text-on-surface-variant'))
        combined.append({
            'ref': f'EXP-{exp.id:05d}',
            'title': exp.title,
            'subtitle': f'{exp.get_category_display()} • {exp.date.strftime("%b %d, %Y")}',
            'amount': exp.amount,
            'is_income': False,
            'status': label,
            'status_class': css,
            'date': exp.date,
        })
    combined = sorted(combined, key=lambda x: x['date'], reverse=True)[:5]
    # Fallback demo rows if empty
    if not combined:
        combined = [
            {'ref': 'TRX-94821', 'title': 'Sunday Offering - Week 2', 'subtitle': 'General Fund • Oct 14, 2023', 'amount': Decimal('1250.00'), 'is_income': True, 'status': 'Completed', 'status_class': 'bg-success/10 text-success'},
            {'ref': 'TRX-94820', 'title': 'Utility Bill - ECG', 'subtitle': 'Operations • Oct 12, 2023', 'amount': Decimal('420.00'), 'is_income': False, 'status': 'Completed', 'status_class': 'bg-success/10 text-success'},
            {'ref': 'TRX-94819', 'title': 'Welfare Support - Mrs. Mensah', 'subtitle': 'Welfare Fund • Oct 11, 2023', 'amount': Decimal('500.00'), 'is_income': False, 'status': 'Pending Approval', 'status_class': 'bg-warning/10 text-warning'},
        ]

    pending_expenses = ExpenseLedger.objects.filter(status='PENDING').select_related('recorded_by').order_by('-date', '-id')[:3]
    pending_count = ExpenseLedger.objects.filter(status='PENDING').count()

    # Statutory mini-tracker demo + real budgets
    statutory_items = []
    for b in Budget.objects.filter(fiscal_year=fiscal_year).order_by('category')[:3]:
        paid = ExpenseLedger.objects.filter(category=b.category, status__in=['APPROVED', 'PAID'], date__year=fiscal_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        pct = int(float(paid) / float(b.allocated_amount) * 100) if b.allocated_amount else 0
        statutory_items.append({
            'label': b.get_category_display(),
            'paid': paid,
            'allocated': b.allocated_amount,
            'pct': min(pct, 100),
        })
    if not statutory_items:
        statutory_items = [
            {'label': 'Circuit Assessment', 'paid': Decimal('400'), 'allocated': Decimal('500'), 'pct': 80},
            {'label': 'Diocese Contribution', 'paid': Decimal('300'), 'allocated': Decimal('600'), 'pct': 50},
            {'label': 'Connexional Levy', 'paid': Decimal('100'), 'allocated': Decimal('400'), 'pct': 25},
        ]

    return render(request, "finance/income/finance_dashboard.html", {
        "active_nav": "finance",
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "month_income": month_income,
        "month_expense": month_expense,
        "month_net": month_net,
        "income_change": income_change,
        "expense_change": expense_change,
        "statutory_due": statutory_due,
        "six_months": six_months,
        "breakdown": breakdown,
        "breakdown_total": breakdown_total,
        "recent_transactions": combined,
        "recent_incomes": recent_incomes,
        "recent_expenses": recent_expenses,
        "pending_expenses": pending_expenses,
        "pending_count": pending_count,
        "statutory_items": statutory_items,
        "today": today,
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
    qs = IncomeLedger.objects.select_related('recorded_by', 'service').all()

    # --- filters ---
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    method = request.GET.get('method', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if q:
        qs = qs.filter(
            Q(remarks__icontains=q)
            | Q(category__icontains=q)
            | Q(recorded_by__username__icontains=q)
            | Q(recorded_by__first_name__icontains=q)
            | Q(reference__icontains=q)
        )
    if category and category != 'ALL':
        qs = qs.filter(category=category)
    if method and method != 'ALL':
        qs = qs.filter(payment_method=method)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    qs = qs.order_by('-date', '-id')

    # --- summary strip (on filtered qs) ---
    agg = qs.aggregate(total=Sum('amount'), avg=Avg('amount'), mx=Max('amount'), cnt=Count('id'))
    total_income = agg['total'] or Decimal('0.00')
    record_count = agg['cnt'] or 0
    avg_tx = agg['avg'] or Decimal('0.00')
    largest = agg['mx'] or Decimal('0.00')

    # --- pagination 25 per page ---
    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_subtotal = sum((i.amount for i in page_obj.object_list), Decimal('0.00')) if page_obj.object_list else Decimal('0.00')

    # Preserve querystring without page param for pagination links
    query_params = request.GET.copy()
    query_params.pop('page', None)
    querystring = query_params.urlencode()

    return render(request, "finance/income/income_ledger.html", {
        "active_nav": "finance",
        "incomes": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "total_income": total_income,
        "record_count": record_count,
        "avg_tx": avg_tx,
        "largest": largest,
        "page_subtotal": page_subtotal,
        "category_choices": IncomeLedger.CATEGORY_CHOICES,
        "method_choices": IncomeLedger.PAYMENT_METHOD_CHOICES,
        "filters": {
            "q": q,
            "category": category or 'ALL',
            "method": method or 'ALL',
            "date_from": date_from,
            "date_to": date_to,
            "querystring": querystring,
        },
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
        return redirect(f"{request.path}?year={year}")

    # --- Dynamic overview ---
    year_param = request.GET.get('year')
    try:
        selected_year = int(year_param) if year_param else timezone.localdate().year
    except ValueError:
        selected_year = timezone.localdate().year

    budgets_qs = Budget.objects.filter(fiscal_year=selected_year).order_by('category')
    # Fallback: if no budgets for selected year, show all years ordered
    if not budgets_qs.exists():
        budgets_qs = Budget.objects.all().order_by('-fiscal_year', 'category')

    enriched = []
    total_budgeted = Decimal('0.00')
    total_spent = Decimal('0.00')
    over_budget = 0
    warning_count = 0

    icon_map = {
        'UTILITIES': 'bolt',
        'WELFARE': 'volunteer_activism',
        'MAINTENANCE': 'home_repair_service',
        'REPAIRS': 'build',
        'TRANSPORT': 'directions_bus',
        'EVANGELISM': 'campaign',
        'ADMIN': 'description',
        'STATUTORY': 'gavel',
        'OTHER': 'category',
    }

    for b in budgets_qs:
        spent = ExpenseLedger.objects.filter(
            category=b.category,
            status__in=['APPROVED', 'PAID'],
            date__year=b.fiscal_year,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        remaining = b.allocated_amount - spent
        pct = int(float(spent) / float(b.allocated_amount) * 100) if b.allocated_amount else 0
        # clamp display width
        pct_display = max(0, min(120, pct))
        bar_width = min(pct_display, 100)
        if pct > 100:
            status = 'over'
            over_budget += 1
        elif pct >= 85:
            status = 'warning'
            warning_count += 1
        else:
            status = 'ok'

        total_budgeted += b.allocated_amount
        total_spent += spent

        enriched.append({
            'obj': b,
            'spent': spent,
            'remaining': remaining,
            'pct': pct,
            'pct_display': pct_display,
            'bar_width': bar_width,
            'status': status,
            'icon': icon_map.get(b.category, 'payments'),
        })

    total_remaining = total_budgeted - total_spent
    utilization = int(float(total_spent) / float(total_budgeted) * 100) if total_budgeted else 0
    # SVG ring: dashoffset = 251.2 * (1 - utilization/100)
    ring_offset = round(251.2 * (1 - utilization / 100), 2) if total_budgeted else 251.2

    # Years list for selector
    years = Budget.objects.values_list('fiscal_year', flat=True).distinct().order_by('-fiscal_year')
    if not years:
        years = [timezone.localdate().year]

    context = {
        "active_nav": "finance",
        "budgets": budgets_qs,
        "enriched_budgets": enriched,
        "category_choices": EXPENSE_CATEGORY_CHOICES,
        "current_year": timezone.localdate().year,
        "selected_year": selected_year,
        "years": years,
        "total_budgeted": total_budgeted,
        "total_spent": total_spent,
        "total_remaining": total_remaining,
        "utilization": utilization,
        "ring_offset": ring_offset,
        "over_budget": over_budget,
        "warning_count": warning_count,
    }
    return render(request, "finance/income/budget_manage.html", context)

@role_required(allowed_roles=['ADMIN', 'TREASURER'])
def record_expense_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', '').strip()
        if category not in dict(EXPENSE_CATEGORY_CHOICES):
            category = 'OTHER'
        amount = request.POST.get('amount', '').strip()
        date = request.POST.get('date', '').strip()
        description = request.POST.get('description', '').strip()
        payment_method = request.POST.get('payment_method', 'CASH').strip().upper()
        if payment_method not in ['CASH', 'MOMO', 'CHEQUE', 'BANK']:
            payment_method = 'CASH'

        if not title or not amount or not date:
            messages.error(request, "Title, amount and date are required.")
            return render(request, "finance/expense/record_expense.html", {
                "active_nav": "finance",
                "category_choices": EXPENSE_CATEGORY_CHOICES,
                "today": timezone.localdate(),
                "form_data": request.POST,
            })

        try:
            Decimal(amount)
        except Exception:
            messages.error(request, "Invalid amount.")
            return render(request, "finance/expense/record_expense.html", {
                "active_nav": "finance",
                "category_choices": EXPENSE_CATEGORY_CHOICES,
                "today": timezone.localdate(),
                "form_data": request.POST,
            })

        ExpenseLedger.objects.create(
            title=title,
            category=category,
            amount=amount,
            date=date,
            recorded_by=request.user,
            description=f"{description}\n[Payment: {payment_method}]" if description else f"[Payment: {payment_method}]",
            status='PENDING'
        )
        messages.success(request, f"Expense voucher for '{title}' submitted for approval.")
        return redirect('finance:expense_approve')

    # Budget hints for current year
    today = timezone.localdate()
    budget_hints = {}
    for b in Budget.objects.filter(fiscal_year=today.year):
        spent = ExpenseLedger.objects.filter(category=b.category, status__in=['APPROVED', 'PAID'], date__year=today.year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        budget_hints[b.category] = {
            'allocated': float(b.allocated_amount),
            'spent': float(spent),
            'remaining': float(b.allocated_amount - spent),
        }

    context = {
        "active_nav": "finance",
        "category_choices": EXPENSE_CATEGORY_CHOICES,
        "today": timezone.localdate(),
        "budget_hints_json": budget_hints,
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
        comment = request.POST.get('comment', '').strip()
        
        expense = get_object_or_404(ExpenseLedger, id=expense_id)
        if action == 'approve':
            expense.status = 'APPROVED'
            expense.approved_by = request.user
            if comment:
                expense.description = (expense.description or '') + f"\n[Approved by {request.user.username}: {comment}]"
            messages.success(request, f"Expense '{expense.title}' approved.")
        elif action == 'reject':
            expense.status = 'REJECTED'
            if comment:
                expense.description = (expense.description or '') + f"\n[Rejected by {request.user.username}: {comment}]"
            messages.info(request, f"Expense '{expense.title}' rejected.")
        expense.save()
        return redirect(f"{request.path}?selected={expense.id}" if action == 'approve' else 'finance:expense_approve')

    pending_qs = ExpenseLedger.objects.filter(status='PENDING').select_related('recorded_by').order_by('-date', '-id')
    pending_expenses = list(pending_qs)

    # Enrich with days waiting
    enriched = []
    today = timezone.localdate()
    for exp in pending_expenses:
        days_waiting = (today - exp.date).days if exp.date else 0
        # Budget check for this category/year
        budget = Budget.objects.filter(fiscal_year=exp.date.year if exp.date else today.year, category=exp.category).first()
        budget_info = None
        if budget:
            spent = ExpenseLedger.objects.filter(category=exp.category, status__in=['APPROVED', 'PAID'], date__year=budget.fiscal_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            remaining = budget.allocated_amount - spent
            budget_info = {'allocated': budget.allocated_amount, 'spent': spent, 'remaining': remaining}
        enriched.append({'obj': exp, 'days_waiting': max(days_waiting, 0), 'budget_info': budget_info})

    # Selected expense (from ?selected= or first pending)
    selected_id = request.GET.get('selected')
    selected = None
    if selected_id:
        try:
            selected = ExpenseLedger.objects.select_related('recorded_by', 'approved_by').get(id=selected_id)
        except ExpenseLedger.DoesNotExist:
            selected = None
    if not selected and pending_expenses:
        selected = pending_expenses[0]
    # For selected, also get days waiting + budget
    selected_days = (today - selected.date).days if selected and selected.date else 0
    selected_budget = None
    if selected:
        b = Budget.objects.filter(fiscal_year=selected.date.year if selected.date else today.year, category=selected.category).first()
        if b:
            s = ExpenseLedger.objects.filter(category=b.category, status__in=['APPROVED', 'PAID'], date__year=b.fiscal_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            selected_budget = {'budget': b, 'spent': s, 'remaining': b.allocated_amount - s}

    pending_expenses = ExpenseLedger.objects.filter(status='PENDING').order_by('-date')
    return render(request, "finance/expense/expence_approve.html", {
        "active_nav": "finance",
        "pending_expenses": pending_expenses,
        "enriched_pending": enriched,
        "pending_count": len(pending_expenses),
        "selected_expense": selected,
        "selected_days": max(selected_days, 0) if selected else 0,
        "selected_budget": selected_budget,
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
