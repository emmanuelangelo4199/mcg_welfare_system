from django.db import models
from django.conf import settings

class GeneratedReportLog(models.Model):
    REPORT_TYPE_CHOICES = [
        ('MEMBERSHIP', 'Membership Report'),
        ('ATTENDANCE', 'Attendance Report'),
        ('FINANCIAL', 'Financial Report'),
        ('WELFARE', 'Welfare Report'),
        ('ANNUAL', 'Annual / Quarterly Report'),
    ]

    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    file_path = models.CharField(max_length=255, blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.title}"
