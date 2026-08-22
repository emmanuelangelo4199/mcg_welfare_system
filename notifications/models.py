from django.db import models
from django.conf import settings


class SystemNotification(models.Model):
    CATEGORY_GENERAL = 'GENERAL'
    CATEGORY_WELFARE = 'WELFARE'
    CATEGORY_FINANCE = 'FINANCE'
    CATEGORY_COMMS = 'COMMS'
    CATEGORY_CLASSES = 'CLASSES'
    CATEGORY_MEMBERS = 'MEMBERS'

    CATEGORY_CHOICES = [
        (CATEGORY_GENERAL, 'General'),
        (CATEGORY_WELFARE, 'Welfare'),
        (CATEGORY_FINANCE, 'Finance'),
        (CATEGORY_COMMS, 'Comms'),
        (CATEGORY_CLASSES, 'Classes'),
        (CATEGORY_MEMBERS, 'Members'),
    ]

    # Presentation metadata used by the notification inbox template.
    CATEGORY_META = {
        CATEGORY_GENERAL: {
            'label': 'General',
            'icon': 'notifications',
            'icon_color': 'text-on-surface-variant',
            'icon_bg': 'bg-surface-container-highest',
        },
        CATEGORY_WELFARE: {
            'label': 'Welfare',
            'icon': 'volunteer_activism',
            'icon_color': 'text-error',
            'icon_bg': 'bg-error-container',
        },
        CATEGORY_FINANCE: {
            'label': 'Finance',
            'icon': 'account_balance_wallet',
            'icon_color': 'text-on-secondary-container',
            'icon_bg': 'bg-secondary-container/30',
        },
        CATEGORY_COMMS: {
            'label': 'Comms',
            'icon': 'campaign',
            'icon_color': 'text-primary',
            'icon_bg': 'bg-primary-muted',
        },
        CATEGORY_CLASSES: {
            'label': 'Classes',
            'icon': 'groups',
            'icon_color': 'text-on-surface-variant',
            'icon_bg': 'bg-surface-container-highest',
        },
        CATEGORY_MEMBERS: {
            'label': 'Members',
            'icon': 'person',
            'icon_color': 'text-blue-600',
            'icon_bg': 'bg-blue-50',
        },
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='system_notifications',
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

    @property
    def meta(self):
        """Presentation metadata (icon, colours, label) for the category."""
        return self.CATEGORY_META.get(self.category, self.CATEGORY_META[self.CATEGORY_GENERAL])


class NotificationPreference(models.Model):
    """Per-user, per-event delivery preferences (email and in-app channels)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    key = models.CharField(max_length=64)
    email = models.BooleanField(default=True)
    in_app = models.BooleanField(default=True)

    class Meta:
        ordering = ['key']
        unique_together = ('user', 'key')

    def __str__(self):
        return f"{self.user.username}: {self.key} (email={self.email}, in_app={self.in_app})"
