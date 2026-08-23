from django.db import models
from django.conf import settings
from members.models import Member


class Organisation(models.Model):
    CATEGORY_CHOICES = [
        ('FELLOWSHIP', 'Fellowship'),
        ('CHOIR', 'Choir'),
        ('YOUTH', 'Youth Ministry'),
        ('MEN', "Men's Fellowship"),
        ('WOMEN', "Women's Fellowship"),
        ('CHILDREN', 'Children Ministry'),
        ('EVANGELISM', 'Evangelism'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='FELLOWSHIP')
    location = models.CharField(max_length=150, blank=True, default='Main Chapel')
    meeting_schedule = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    president = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_organisations'
    )
    secretary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='secretary_organisations'
    )
    treasurer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='treasurer_organisations'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        # Prefer explicit memberships if they exist, otherwise fallback to M2M members
        membership_count = self.memberships.count()
        if membership_count > 0:
            return membership_count
        return self.members.count() if hasattr(self, 'members') else 0

    @property
    def active_member_count(self):
        membership_active = self.memberships.filter(is_active=True).count()
        if membership_active > 0 or self.memberships.exists():
            return membership_active
        if hasattr(self, 'members'):
            return self.members.filter(status='ACTIVE').count()
        return 0

    @property
    def total_dues(self):
        return self.dues.aggregate(total=models.Sum('amount'))['total'] or 0


class OrganisationMembership(models.Model):
    ROLE_CHOICES = [
        ('PRESIDENT', 'President'),
        ('VICE_PRESIDENT', 'Vice President'),
        ('SECRETARY', 'Secretary'),
        ('TREASURER', 'Treasurer'),
        ('MEMBER', 'Member'),
    ]

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='memberships')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='organisation_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organisation', 'member')
        ordering = ['-joined_date']

    def __str__(self):
        return f"{self.member.get_full_name()} - {self.organisation.name} ({self.role})"


class OrganisationDues(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='dues')
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='org_dues')
    member_name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    date_paid = models.DateField()
    receipt_number = models.CharField(max_length=100, blank=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_org_dues')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-date_paid', '-created_at']
        indexes = [
            models.Index(fields=['date_paid']),
        ]

    def __str__(self):
        return f"{self.organisation.name} Dues - {self.member_name} (GHS {self.amount})"


class OrganisationMeeting(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='meetings')
    date = models.DateField()
    topic = models.CharField(max_length=200, blank=True)
    venue = models.CharField(max_length=150, blank=True)
    minutes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('organisation', 'date')

    def __str__(self):
        return f"{self.organisation.name} - {self.date}"