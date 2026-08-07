from django.contrib import admin
from .models import IncomeLedger, ExpenseLedger, Budget

@admin.register(IncomeLedger)
class IncomeLedgerAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'date', 'recorded_by')
    list_filter = ('category', 'date')

@admin.register(ExpenseLedger)
class ExpenseLedgerAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'amount', 'date', 'status', 'approved_by')
    list_filter = ('status', 'category', 'date')

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('fiscal_year', 'category', 'allocated_amount')
