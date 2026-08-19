from django.db import models
from django.conf import settings
from classes.models import ClassGroup

class Member(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    MARITAL_STATUS_CHOICES = [
        ('SINGLE', 'Single'),
        ('MARRIED', 'Married'),
        ('WIDOWED', 'Widowed'),
        ('DIVORCED', 'Divorced'),
    ]
    MEMBERSHIP_TYPE_CHOICES = [
        ('FULL', 'Full Member'),
        ('TRIAL', 'Member on Trial'),
        ('ADHERENT', 'Adherent'),
    ]
    STATUS_CHOICES = [
        ('ACTIVE', 'Active Full Member'),
        ('PENDING', 'Pending Approval'),
        ('REGULARIZED', 'Regularized'),
        ('TRANSFERRED', 'Transferred'),
        ('INACTIVE', 'Inactive'),
        ('DECLINED', 'Regularisation Declined'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='member_record'
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(blank=True, null=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)
    occupation = models.CharField(max_length=150, blank=True, null=True)
    hometown = models.CharField(max_length=150, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    residential_address = models.TextField(blank=True, null=True)
    
    assigned_class = models.ForeignKey(
        ClassGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    organisations = models.ManyToManyField(
        'organisations.Organisation',
        blank=True,
        related_name='members'
    )
    membership_type = models.CharField(max_length=20, choices=MEMBERSHIP_TYPE_CHOICES, default='FULL')
    date_of_baptism = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    emergency_contact_name = models.CharField(max_length=150, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    passport_photo = models.FileField(upload_to='member_photos/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_status_display()})"

class MemberRegularisation(models.Model):
    DECISION_CHOICES = [
        ('APPROVED', 'Approved for Full Membership'),
        ('DEFERRED', 'Deferred (Requires Action)'),
        ('DECLINED', 'Declined'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='regularisations')
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    meeting_reference = models.CharField(max_length=100, blank=True, null=True)
    approval_date = models.DateField()
    assigned_class = models.ForeignKey(
        ClassGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='regularisation_decisions'
    )
    remarks = models.TextField(blank=True, null=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_regularisations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-approval_date', '-created_at']

    def __str__(self):
        return f"{self.member.get_full_name()} — {self.get_decision_display()}"


class MembershipStatusChange(models.Model):
    """Audit record for every membership status modification."""

    AUTHORISED_BY_CHOICES = [
        ('MINISTER', 'Rev. Superintendent Minister'),
        ('STEWARD', 'Society Steward'),
        ('LEADERS_MEETING', 'Leaders Meeting'),
    ]

    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='status_changes'
    )
    previous_status = models.CharField(max_length=20, choices=Member.STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=Member.STATUS_CHOICES)
    effective_date = models.DateField()
    reason = models.TextField()
    authorised_by = models.CharField(max_length=30, choices=AUTHORISED_BY_CHOICES)
    note_reference = models.CharField(max_length=200, blank=True, default='')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_status_changes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.member.get_full_name()}: "
            f"{self.get_previous_status_display()} -> {self.get_new_status_display()}"
        )