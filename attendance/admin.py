from django.contrib import admin
from .models import ServiceAttendance, ClassAttendanceRecord, OrganisationAttendanceRecord, AttendanceSummary, AbsenteeFollowUp


@admin.register(ServiceAttendance)
class ServiceAttendanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'service', 'service_date', 'male_count', 'female_count', 'children_count', 'total_count', 'recorded_by', 'recorded_at')
    list_filter = ('service_date', 'recorded_at', 'service__service_type')
    search_fields = ('service__title', 'notes')
    readonly_fields = ('total_count', 'recorded_at', 'updated_at')
    ordering = ('-service_date', '-recorded_at')


@admin.register(ClassAttendanceRecord)
class ClassAttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'class_group', 'date', 'present_count', 'absent_count', 'attendance_rate', 'recorded_by', 'created_at')
    list_filter = ('date', 'created_at', 'class_group')
    search_fields = ('class_group__name', 'remarks')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('present_members',)


@admin.register(OrganisationAttendanceRecord)
class OrganisationAttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'organisation', 'date', 'attendees_count', 'male_count', 'female_count', 'recorded_by', 'created_at')
    list_filter = ('date', 'organisation')
    search_fields = ('organisation__name', 'remarks')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'total_service_attendance', 'total_class_attendance', 'total_org_attendance', 'total_absentees', 'created_at')
    list_filter = ('date',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AbsenteeFollowUp)
class AbsenteeFollowUpAdmin(admin.ModelAdmin):
    list_display = ('id', 'member', 'absence_date', 'reason', 'follow_up_status', 'followed_up_by', 'followed_up_at', 'created_at')
    list_filter = ('follow_up_status', 'absence_date')
    search_fields = ('member__first_name', 'member__last_name', 'reason')
    readonly_fields = ('created_at',)