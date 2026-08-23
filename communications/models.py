from django.db import models
from django.conf import settings


class Announcement(models.Model):
    CATEGORY_CHOICES = [
        ('GENERAL', 'General'),
        ('EVENT', 'Event'),
        ('WELFARE', 'Welfare'),
        ('FINANCE', 'Finance'),
        ('URGENT', 'Urgent'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GENERAL')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    expiry_date = models.DateField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        from django.utils import timezone
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False


class OutgoingMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
        ('WHATSAPP', 'WhatsApp'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('SCHEDULED', 'Scheduled'),
    ]

    recipient_group = models.CharField(max_length=100)
    recipient_count = models.PositiveIntegerField(default=0)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='SMS')
    subject = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SENT')
    failure_reason = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='outgoing_messages')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['message_type', 'status']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"[{self.message_type}] {self.recipient_group} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"


class MessageTemplate(models.Model):
    """Reusable message templates for birthdays, reminders, etc."""
    TEMPLATE_TYPE_CHOICES = [
        ('BIRTHDAY', 'Birthday'),
        ('DUE_REMINDER', 'Dues Reminder'),
        ('WELFARE', 'Welfare'),
        ('GENERAL', 'General'),
        ('ANNOUNCEMENT', 'Announcement'),
    ]

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, default='GENERAL')
    message_type = models.CharField(max_length=20, choices=OutgoingMessage.MESSAGE_TYPE_CHOICES, default='SMS')
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField(help_text="Use {{name}} {{amount}} {{date}} placeholders")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class CommunicationLog(models.Model):
    """Per-recipient delivery log for detailed tracking"""
    outgoing_message = models.ForeignKey(OutgoingMessage, on_delete=models.CASCADE, related_name='delivery_logs')
    recipient_name = models.CharField(max_length=150)
    recipient_contact = models.CharField(max_length=100, blank=True)  # phone or email
    status = models.CharField(max_length=20, choices=OutgoingMessage.STATUS_CHOICES, default='SENT')
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient_name} - {self.status}"