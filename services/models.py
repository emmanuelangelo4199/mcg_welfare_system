from django.db import models
from django.conf import settings
from members.models import Member


class ChurchService(models.Model):
    SERVICE_TYPE_CHOICES = [
        ('SUNDAY', 'Sunday Service'),
        ('WEEKDAY', 'Weekday Service'),
        ('BIBLE_STUDY', 'Bible Study'),
        ('PRAYER', 'Prayer Meeting'),
        ('REVIVAL', 'Revival / Crusade'),
        ('FUNERAL', 'Funeral Service'),
        ('WEDDING', 'Wedding'),
        ('SPECIAL', 'Special Programme'),
        ('OTHER', 'Other'),
    ]
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('POSTPONED', 'Postponed'),
    ]

    title = models.CharField(max_length=200)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, default='SUNDAY')
    description = models.TextField(blank=True)
    service_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    location = models.CharField(max_length=200, default='Main Auditorium')
    theme = models.CharField(max_length=255, blank=True, null=True)
    preacher = models.CharField(max_length=150, blank=True, null=True)
    liturgist = models.CharField(max_length=150, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    is_featured = models.BooleanField(default=False)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_services')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['service_date', 'start_time']
        indexes = [
            models.Index(fields=['service_date', 'status']),
            models.Index(fields=['service_type']),
        ]

    def __str__(self):
        return f"{self.title} ({self.service_date})"

    @property
    def duration_minutes(self):
        if self.start_time and self.end_time:
            from datetime import datetime, time
            # Handle both string and time objects
            start_t = self.start_time
            end_t = self.end_time
            if isinstance(start_t, str):
                try:
                    start_t = datetime.strptime(start_t, "%H:%M").time()
                except ValueError:
                    try:
                        start_t = datetime.strptime(start_t, "%H:%M:%S").time()
                    except ValueError:
                        return None
            if isinstance(end_t, str):
                try:
                    end_t = datetime.strptime(end_t, "%H:%M").time()
                except ValueError:
                    try:
                        end_t = datetime.strptime(end_t, "%H:%M:%S").time()
                    except ValueError:
                        return None

            if isinstance(start_t, time) and isinstance(end_t, time):
                start = datetime.combine(datetime.today(), start_t)
                end = datetime.combine(datetime.today(), end_t)
                delta = end - start
                return int(delta.total_seconds() // 60)
        return None

    @property
    def is_upcoming(self):
        from django.utils import timezone
        return self.service_date >= timezone.now().date() and self.status == 'SCHEDULED'

    @property
    def attendance_count(self):
        return self.attendances.filter(is_present=True).count()


class ServiceProgramItem(models.Model):
    """Order of service / programme items"""
    service = models.ForeignKey(ChurchService, on_delete=models.CASCADE, related_name='program_items')
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=5)
    responsible_person = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.title} - {self.service.title}"


class ServiceAttendance(models.Model):
    service = models.ForeignKey(ChurchService, on_delete=models.CASCADE, related_name='attendances')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, null=True, blank=True, related_name='service_attendances')
    guest_name = models.CharField(max_length=150, blank=True, help_text="For guests not in member directory")
    is_present = models.BooleanField(default=True)
    is_guest = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        unique_together = ('service', 'member')

    def __str__(self):
        name = self.member.get_full_name() if self.member else self.guest_name
        return f"{name} - {self.service.title} - {'Present' if self.is_present else 'Absent'}"