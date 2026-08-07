from django.db import models
from services.models import ChurchService
from classes.models import ClassGroup
from members.models import Member

class ServiceAttendance(models.Model):
    service = models.ForeignKey(ChurchService, on_delete=models.CASCADE, related_name='attendance_records')
    male_count = models.PositiveIntegerField(default=0)
    female_count = models.PositiveIntegerField(default=0)
    children_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_count = self.male_count + self.female_count + self.children_count
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service.title} Attendance - Total: {self.total_count}"

class ClassAttendanceRecord(models.Model):
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    present_members = models.ManyToManyField(Member, blank=True, related_name='class_attendances')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.class_group.name} - {self.date}"
