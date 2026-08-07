from django.contrib import admin
from .models import GeneratedReportLog

@admin.register(GeneratedReportLog)
class GeneratedReportLogAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'title', 'generated_by', 'generated_at')
    list_filter = ('report_type',)
