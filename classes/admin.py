from django.contrib import admin
from .models import ClassGroup, ClassMeeting


class ClassMeetingInline(admin.TabularInline):
    model = ClassMeeting
    extra = 1
    ordering = ('-date',)


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'leader', 'assistant_leader', 'meeting_time', 'location', 'capacity', 'member_count', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'meeting_time', 'location')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ClassMeetingInline]
    ordering = ('name',)


@admin.register(ClassMeeting)
class ClassMeetingAdmin(admin.ModelAdmin):
    list_display = ('id', 'class_group', 'date', 'topic', 'start_time', 'end_time', 'created_by', 'created_at')
    list_filter = ('date', 'class_group__category')
    search_fields = ('class_group__name', 'topic', 'notes')
    readonly_fields = ('created_at',)
    ordering = ('-date',)