from django.contrib import admin
from .models import SystemNotification, NotificationPreference

@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'category', 'is_read', 'created_at')
    list_filter = ('category', 'is_read')
    search_fields = ('title', 'message')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'email', 'in_app')
    list_filter = ('email', 'in_app')
    search_fields = ('user__username', 'key')
