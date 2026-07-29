from django.shortcuts import render

def finance_dashboard_view(request):
    return render(request, "finance/income/finance_dashboard.html")

def record_income_view(request):
    return render(request, "finance/income/record_income.html")

def income_ledger_view(request):
    return render(request, "finance/income/income_ledger.html")

def budget_manage_view(request):
    return render(request, "finance/income/budget_manage.html")

def record_expense_view(request):
    return render(request, "finance/expense/record_expense.html")

def expense_ledger_view(request):
    return render(request, "finance/expense/expence_ledger.html")

def expense_approve_view(request):
    return render(request, "finance/expense/expence_approve.html")

def cashbook_view(request):
    return render(request, "finance/report/cashbook_view.html")

def receipt_payment_report_view(request):
    return render(request, "finance/report/recepit_pay.html")

def payment_tracker_view(request):
    return render(request, "finance/report/stat_payment_tracker.html")
