from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.finance_dashboard_view, name='dashboard'),
    path('income/record/', views.record_income_view, name='record_income'),
    path('income/ledger/', views.income_ledger_view, name='income_ledger'),
    path('budget/', views.budget_manage_view, name='budget_manage'),
    path('expense/record/', views.record_expense_view, name='record_expense'),
    path('expense/ledger/', views.expense_ledger_view, name='expense_ledger'),
    path('expense/approve/', views.expense_approve_view, name='expense_approve'),
    path('reports/cashbook/', views.cashbook_view, name='cashbook'),
    path('reports/receipt-payment/', views.receipt_payment_report_view, name='receipt_payment_report'),
    path('reports/payment-tracker/', views.payment_tracker_view, name='payment_tracker'),
]
