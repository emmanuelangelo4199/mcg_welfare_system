from django.contrib import admin
from .models import Announcement, OutgoingMessage, MessageTemplate, CommunicationLog


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'priority', 'is_active', 'is_pinned', 'views_count', 'created_by', 'created_at', 'expiry_date')
    list_filter = ('category', 'priority', 'is_active', 'is_pinned', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('views_count', 'created_at', 'updated_at')
    ordering = ('-is_pinned', '-created_at')


@admin.register(OutgoingMessage)
class OutgoingMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'message_type', 'recipient_group', 'recipient_count', 'subject', 'status', 'created_by', 'sent_at')
    list_filter = ('message_type', 'status', 'sent_at')
    search_fields = ('recipient_group', 'subject', 'content')
    readonly_fields = ('sent_at', 'updated_at')


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'template_type', 'message_type', 'is_active', 'updated_at')
    list_filter = ('template_type', 'message_type', 'is_active')
    search_fields = ('code', 'name', 'subject', 'content')


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'outgoing_message', 'recipient_name', 'recipient_contact', 'status', 'delivered_at', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('recipient_name', 'recipient_contact')