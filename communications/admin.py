from django.contrib import admin
from .models import Announcement, OutgoingMessage

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_by', 'created_at')

@admin.register(OutgoingMessage)
class OutgoingMessageAdmin(admin.ModelAdmin):
    list_display = ('recipient_group', 'message_type', 'subject', 'sent_at')
