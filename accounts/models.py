from django.db import models
from django.conf import settings

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('TREASURER', 'Treasurer'),
        ('CLASS_LEADER', 'Class Leader'),
        ('WELFARE_OFFICER', 'Welfare Officer'),
        ('MEMBER', 'Society Member'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    title = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
