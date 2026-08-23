from django.contrib import admin
from .models import WelfareCase, VisitationLog, WelfareDisbursement, WelfareCaseActivity


@admin.register(WelfareCase)
class WelfareCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'member', 'case_type', 'title', 'requested_amount', 'approved_amount', 'status', 'priority', 'is_confidential', 'assigned_officer', 'created_at')
    list_filter = ('case_type', 'status', 'priority', 'is_confidential', 'created_at')
    search_fields = ('member__first_name', 'member__last_name', 'title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'closed_at')
    list_select_related = ('member', 'assigned_officer')
    ordering = ('-created_at',)


@admin.register(VisitationLog)
class VisitationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'welfare_case', 'visit_date', 'visitors', 'created_by', 'created_at')
    list_filter = ('visit_date', 'created_at')
    search_fields = ('welfare_case__title', 'visitors', 'findings')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(WelfareDisbursement)
class WelfareDisbursementAdmin(admin.ModelAdmin):
    list_display = ('id', 'welfare_case', 'amount', 'disbursement_date', 'payment_method', 'reference_number', 'created_by', 'created_at')
    list_filter = ('payment_method', 'disbursement_date')
    search_fields = ('welfare_case__title', 'reference_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(WelfareCaseActivity)
class WelfareCaseActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'welfare_case', 'action', 'performed_by', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('welfare_case__title', 'description')
    readonly_fields = ('created_at',)