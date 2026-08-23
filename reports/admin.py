from django.contrib import admin
from .models import GeneratedReportLog, ReportSchedule, ReportFavorite


@admin.register(GeneratedReportLog)
class GeneratedReportLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_type', 'title', 'status', 'is_pinned', 'file_size_formatted', 'generated_by', 'generated_at')
    list_filter = ('report_type', 'status', 'is_pinned', 'generated_at')
    search_fields = ('title', 'description')
    readonly_fields = ('file_size', 'generated_at', 'updated_at')
    ordering = ('-is_pinned', '-generated_at')


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_type', 'title', 'frequency', 'is_active', 'next_run', 'last_run', 'created_by')
    list_filter = ('report_type', 'frequency', 'is_active')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReportFavorite)
class ReportFavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'report', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'report__title')