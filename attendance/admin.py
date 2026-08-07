from django.contrib import admin
from .models import ServiceAttendance, ClassAttendanceRecord

@admin.register(ServiceAttendance)
class ServiceAttendanceAdmin(admin.ModelAdmin):
    list_display = ('service', 'male_count', 'female_count', 'children_count', 'total_count', 'recorded_at')

@admin.register(ClassAttendanceRecord)
class ClassAttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('class_group', 'date')
