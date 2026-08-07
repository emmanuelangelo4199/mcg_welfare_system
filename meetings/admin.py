from django.contrib import admin
from .models import Meeting, ActionItem

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'start_time', 'location')

@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ('task', 'meeting', 'assigned_to', 'due_date', 'is_completed')
    list_filter = ('is_completed', 'due_date')
