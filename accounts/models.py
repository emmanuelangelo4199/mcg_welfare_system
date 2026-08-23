from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('SUPERINTENDENT_MINISTER', 'Superintendent Minister'),
        ('SOCIETY_STEWARD', 'Society Steward'),
        ('LEADERS_MEETING_SECRETARY', 'Leaders’ Meeting Secretary'),
        ('AUDITOR', 'Auditor'),
        ('TREASURER', 'Treasurer'),
        ('CATECHIST', 'Catechist'),
        ('CIRCUIT_MINISTER', 'Circuit Minister'),
        ('BIBLE_STUDY_LEADER', 'Bible Study Leaders'),
        ('CLASS_LEADER', 'Class Leader'),
        ('ORGANISATION_LEADER', 'Organisation Leaders'),
        ('FINANCIAL_SECRETARY', 'Financial Secretary'),
        ('SOCIETY_MINISTER', 'Society Minister'),
        ('WELFARE_OFFICER', 'Welfare Officer'),
        ('MEMBER', 'Society Member'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(max_length=40, choices=ROLE_CHOICES, default='MEMBER')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    title = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Role(models.Model):
    """
    Canonical role definition for permission management.
    Mirrors UserProfile.ROLE_CHOICES but allows dynamic metadata.
    """
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system_protected = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def user_count(self):
        return UserProfile.objects.filter(role=self.code).count()


class Module(models.Model):
    """
    System module for permission matrix (Members, Finance, Welfare, etc.)
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_sensitive = models.BooleanField(default=False, help_text="Marks sensitive modules like Welfare")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    Permission matrix: what each role can do per module.
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='role_permissions')

    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('role', 'module')
        ordering = ['role__name', 'module__order']

    def __str__(self):
        return f"{self.role.name} - {self.module.name}"

    def has_any(self):
        return any([self.can_view, self.can_create, self.can_edit, self.can_delete, self.can_approve])