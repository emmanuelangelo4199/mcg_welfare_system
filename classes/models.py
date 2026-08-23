from django.db import models
from django.conf import settings


class ClassGroup(models.Model):
    CATEGORY_CHOICES = [
        ('BIBLE_STUDY', 'Bible Study'),
        ('SUNDAY_SCHOOL', 'Sunday School'),
        ('YOUTH', 'Youth Class'),
        ('ADULT', 'Adult Class'),
        ('NEW_CONVERT', 'New Convert'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='BIBLE_STUDY')
    location = models.CharField(max_length=150, blank=True, default='Main Chapel')
    meeting_time = models.CharField(max_length=100, blank=True, null=True)
    capacity = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_classes'
    )
    assistant_leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assisted_classes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bible Study Class'
        verbose_name_plural = 'Bible Study Classes'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.filter(status='ACTIVE').count() if hasattr(self, 'members') else 0

    @property
    def total_members(self):
        return self.members.count() if hasattr(self, 'members') else 0

    @property
    def occupancy_rate(self):
        if self.capacity > 0:
            return (self.member_count / self.capacity) * 100
        return 0

    @property
    def is_full(self):
        return self.member_count >= self.capacity


class ClassMeeting(models.Model):
    """Individual class meeting / session"""
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name='meetings')
    date = models.DateField()
    topic = models.CharField(max_length=200, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('class_group', 'date')

    def __str__(self):
        return f"{self.class_group.name} - {self.date}"