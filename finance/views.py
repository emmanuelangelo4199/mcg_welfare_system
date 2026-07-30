from django.shortcuts import render

def finance_dashboard_view(request):
    return render(request, "finance/income/finance_dashboard.html", {"active_nav": "finance"})

def record_income_view(request):
    return render(request, "finance/income/record_income.html", {"active_nav": "finance"})

def income_ledger_view(request):
    return render(request, "finance/income/income_ledger.html", {"active_nav": "finance"})

def budget_manage_view(request):
    return render(request, "finance/income/budget_manage.html", {"active_nav": "finance"})

def record_expense_view(request):
    return render(request, "finance/expense/record_expense.html", {"active_nav": "finance"})

def expense_ledger_view(request):
    return render(request, "finance/expense/expence_ledger.html", {"active_nav": "finance"})

def expense_approve_view(request):
    return render(request, "finance/expense/expence_approve.html", {"active_nav": "finance"})

def cashbook_view(request):
    return render(request, "finance/report/cashbook_view.html", {"active_nav": "finance"})

def receipt_payment_report_view(request):
    return render(request, "finance/report/recepit_pay.html", {"active_nav": "finance"})

def payment_tracker_view(request):
    return render(request, "finance/report/stat_payment_tracker.html", {"active_nav": "finance"})
