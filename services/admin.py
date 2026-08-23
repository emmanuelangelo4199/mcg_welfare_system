from django.contrib import admin
from .models import ChurchService, ServiceProgramItem, ServiceAttendance


class ServiceProgramItemInline(admin.TabularInline):
    model = ServiceProgramItem
    extra = 1
    ordering = ('order',)


class ServiceAttendanceInline(admin.TabularInline):
    model = ServiceAttendance
    extra = 0
    readonly_fields = ('recorded_at',)


@admin.register(ChurchService)
class ChurchServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'service_type', 'service_date', 'start_time', 'end_time', 'status', 'is_featured', 'preacher', 'attendance_count', 'created_at')
    list_filter = ('service_type', 'status', 'is_featured', 'service_date')
    search_fields = ('title', 'theme', 'preacher', 'liturgist', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ServiceProgramItemInline, ServiceAttendanceInline]
    ordering = ('-service_date', '-start_time')


@admin.register(ServiceProgramItem)
class ServiceProgramItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'service', 'order', 'title', 'duration_minutes', 'responsible_person')
    list_filter = ('service__service_type',)
    search_fields = ('title', 'service__title', 'responsible_person')
    ordering = ('service', 'order')


@admin.register(ServiceAttendance)
class ServiceAttendanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'service', 'member', 'guest_name', 'is_present', 'is_guest', 'recorded_by', 'recorded_at')
    list_filter = ('is_present', 'is_guest', 'service__service_type', 'recorded_at')
    search_fields = ('member__first_name', 'member__last_name', 'guest_name', 'service__title')
    readonly_fields = ('recorded_at',)