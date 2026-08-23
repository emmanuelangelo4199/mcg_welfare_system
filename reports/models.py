from django.db import models
from django.conf import settings


class GeneratedReportLog(models.Model):
    REPORT_TYPE_CHOICES = [
        ('MEMBERSHIP', 'Membership Report'),
        ('ATTENDANCE', 'Attendance Report'),
        ('FINANCIAL', 'Financial Report'),
        ('WELFARE', 'Welfare Report'),
        ('ANNUAL', 'Annual / Quarterly Report'),
        ('CUSTOM', 'Custom Report'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('GENERATED', 'Generated'),
        ('FAILED', 'Failed'),
        ('ARCHIVED', 'Archived'),
    ]

    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    parameters = models.JSONField(default=dict, blank=True, help_text="Filters used to generate report")
    file_path = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='GENERATED')
    is_pinned = models.BooleanField(default=False)

    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-generated_at']
        indexes = [
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['generated_at']),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.title}"

    @property
    def file_size_formatted(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024*1024:
            return f"{self.file_size/1024:.1f} KB"
        else:
            return f"{self.file_size/(1024*1024):.1f} MB"


class ReportSchedule(models.Model):
    """Scheduled automatic report generation"""
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUALLY', 'Annually'),
    ]

    report_type = models.CharField(max_length=30, choices=GeneratedReportLog.REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='MONTHLY')
    parameters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    next_run = models.DateTimeField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_run']

    def __str__(self):
        return f"{self.title} - {self.frequency}"


class ReportFavorite(models.Model):
    """User favorite reports"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_reports')
    report = models.ForeignKey(GeneratedReportLog, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'report')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.report.title}"