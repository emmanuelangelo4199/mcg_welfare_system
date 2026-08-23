from django.db import models
from django.conf import settings
from services.models import ChurchService
from classes.models import ClassGroup
from organisations.models import Organisation
from members.models import Member


class ServiceAttendance(models.Model):
    """Aggregated attendance counts per service (male/female/children)"""
    service = models.ForeignKey(ChurchService, on_delete=models.CASCADE, related_name='attendance_records')
    service_date = models.DateField(null=True, blank=True, help_text="Date of service, defaults to service date")
    male_count = models.PositiveIntegerField(default=0)
    female_count = models.PositiveIntegerField(default=0)
    children_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_attendance_records')
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-service_date', '-recorded_at']
        indexes = [
            models.Index(fields=['service_date']),
            models.Index(fields=['recorded_at']),
        ]

    def save(self, *args, **kwargs):
        self.total_count = self.male_count + self.female_count + self.children_count
        if not self.service_date and self.service:
            self.service_date = self.service.service_date
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service.title} Attendance - Total: {self.total_count}"

    @property
    def male_percentage(self):
        return (self.male_count / self.total_count * 100) if self.total_count else 0

    @property
    def female_percentage(self):
        return (self.female_count / self.total_count * 100) if self.total_count else 0


class ClassAttendanceRecord(models.Model):
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    present_members = models.ManyToManyField(Member, blank=True, related_name='class_attendances')
    remarks = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='class_attendance_records')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ('class_group', 'date')
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.class_group.name} - {self.date}"

    @property
    def present_count(self):
        return self.present_members.count()

    @property
    def absent_count(self):
        total = self.class_group.members.filter(status='ACTIVE').count() if hasattr(self.class_group, 'members') else 0
        return max(0, total - self.present_count)

    @property
    def attendance_rate(self):
        total = self.class_group.members.filter(status='ACTIVE').count() if hasattr(self.class_group, 'members') else 0
        return (self.present_count / total * 100) if total else 0


class OrganisationAttendanceRecord(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    attendees_count = models.PositiveIntegerField(default=0)
    male_count = models.PositiveIntegerField(default=0)
    female_count = models.PositiveIntegerField(default=0)
    remarks = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='org_attendance_records')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.organisation.name} - {self.date}"


class AttendanceSummary(models.Model):
    """Daily summary across all attendance types"""
    date = models.DateField(unique=True)
    total_service_attendance = models.PositiveIntegerField(default=0)
    total_class_attendance = models.PositiveIntegerField(default=0)
    total_org_attendance = models.PositiveIntegerField(default=0)
    total_absentees = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Summary {self.date} - Total: {self.total_service_attendance + self.total_class_attendance + self.total_org_attendance}"


class AbsenteeFollowUp(models.Model):
    """Track follow-up for absentees"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending Follow-up'),
        ('CONTACTED', 'Contacted'),
        ('VISITED', 'Visited'),
        ('RESOLVED', 'Resolved'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='absentee_followups')
    absence_date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)
    follow_up_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    follow_up_notes = models.TextField(blank=True)
    followed_up_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    followed_up_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-absence_date', '-created_at']
        unique_together = ('member', 'absence_date')

    def __str__(self):
        return f"{self.member.get_full_name()} - Absent {self.absence_date} - {self.follow_up_status}"