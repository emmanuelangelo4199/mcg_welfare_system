from django.db import models
from django.conf import settings
from members.models import Member


class WelfareCase(models.Model):
    CASE_TYPE_CHOICES = [
        ('MEDICAL', 'Medical Emergency'),
        ('BEREAVEMENT', 'Bereavement / Funeral Support'),
        ('HARDSHIP', 'Financial Hardship'),
        ('EDUCATION', 'Education / Scholarship'),
        ('OTHER', 'Other Support'),
    ]
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('DISBURSED', 'Disbursed'),
        ('CLOSED', 'Closed'),
        ('REJECTED', 'Rejected'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='welfare_cases')
    case_type = models.CharField(max_length=30, choices=CASE_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    is_confidential = models.BooleanField(default=True, help_text="Marks case as confidential")
    review_notes = models.TextField(blank=True, help_text="Internal review notes")

    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cases'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_welfare_cases'
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['case_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.get_case_type_display()}] {self.member.get_full_name()} - {self.title}"

    @property
    def is_open(self):
        return self.status not in ['CLOSED', 'REJECTED']

    @property
    def disbursement_percentage(self):
        if self.requested_amount and self.requested_amount > 0:
            return (self.approved_amount / self.requested_amount) * 100
        return 0

    def can_transition_to(self, new_status):
        """Validate status transitions"""
        valid_transitions = {
            'SUBMITTED': ['UNDER_REVIEW', 'REJECTED'],
            'UNDER_REVIEW': ['APPROVED', 'REJECTED', 'SUBMITTED'],
            'APPROVED': ['DISBURSED', 'REJECTED', 'UNDER_REVIEW'],
            'DISBURSED': ['CLOSED'],
            'CLOSED': [],
            'REJECTED': ['SUBMITTED', 'UNDER_REVIEW'],
        }
        return new_status in valid_transitions.get(self.status, [])


class VisitationLog(models.Model):
    welfare_case = models.ForeignKey(WelfareCase, on_delete=models.CASCADE, related_name='visitations')
    visit_date = models.DateField()
    visitors = models.CharField(max_length=255, help_text="Comma separated list of visiting committee members")
    findings = models.TextField()
    recommendation = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visitation_logs'
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-visit_date', '-created_at']

    def __str__(self):
        return f"Visit on {self.visit_date} for Case #{self.welfare_case.id}"


class WelfareDisbursement(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
    ]

    welfare_case = models.OneToOneField(WelfareCase, on_delete=models.CASCADE, related_name='disbursement')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    disbursement_date = models.DateField()
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='MOBILE_MONEY')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disbursements'
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-disbursement_date']


    def __str__(self):
        return f"Disbursement GHS {self.amount} for Case #{self.welfare_case.id}"

class WelfareCaseActivity(models.Model):
    """Audit trail for welfare case actions"""
    ACTION_CHOICES = [
        ('CREATED', 'Case Created'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('ASSIGNED', 'Officer Assigned'),
        ('VISIT_LOGGED', 'Visitation Logged'),
        ('DISBURSED', 'Disbursement Recorded'),
        ('NOTE_ADDED', 'Note Added'),
        ('CLOSED', 'Case Closed'),
    ]

    welfare_case = models.ForeignKey(WelfareCase, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='welfare_activities'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Welfare case activities"

    def __str__(self):
        return f"{self.get_action_display()} - Case #{self.welfare_case.id} at {self.created_at.strftime('%Y-%m-%d')}"