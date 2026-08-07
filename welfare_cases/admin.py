from django.contrib import admin
from .models import WelfareCase, VisitationLog, WelfareDisbursement

@admin.register(WelfareCase)
class WelfareCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'member', 'case_type', 'title', 'requested_amount', 'approved_amount', 'status', 'created_at')
    list_filter = ('case_type', 'status')
    search_fields = ('member__first_name', 'member__last_name', 'title')

@admin.register(VisitationLog)
class VisitationLogAdmin(admin.ModelAdmin):
    list_display = ('welfare_case', 'visit_date', 'visitors')

@admin.register(WelfareDisbursement)
class WelfareDisbursementAdmin(admin.ModelAdmin):
    list_display = ('welfare_case', 'amount', 'disbursement_date', 'payment_method', 'reference_number')
