from django.db import models
from django.conf import settings

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class OutgoingMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
        ('WHATSAPP', 'WhatsApp'),
    ]
    recipient_group = models.CharField(max_length=100)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='SMS')
    subject = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.message_type}] {self.recipient_group} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"
