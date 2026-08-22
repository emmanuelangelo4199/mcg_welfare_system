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
    CLOSURE_OUTCOME_CHOICES = [
        ('RESOLVED', 'Resolved / Improved'),
        ('DECEASED', 'Deceased'),
        ('TRANSFERRED', 'Transferred to External Org'),
        ('WITHDRAWN', 'Member Withdrawn'),
        ('OTHER', 'Other'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='welfare_cases')
    case_type = models.CharField(max_length=30, choices=CASE_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_cases'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closure_outcome = models.CharField(max_length=20, choices=CLOSURE_OUTCOME_CHOICES, blank=True, null=True)
    closure_notes = models.TextField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"[{self.get_case_type_display()}] {self.member.get_full_name()} - {self.title}"

class VisitationLog(models.Model):
    welfare_case = models.ForeignKey(WelfareCase, on_delete=models.CASCADE, related_name='visitations')
    visit_date = models.DateField()
    visitors = models.CharField(max_length=255, help_text="Comma separated list of visiting committee members")
    findings = models.TextField()
    recommendation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Visit on {self.visit_date} for Case #{self.welfare_case.id}"

class WelfareDisbursement(models.Model):
    welfare_case = models.OneToOneField(WelfareCase, on_delete=models.CASCADE, related_name='disbursement')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    disbursement_date = models.DateField()
    payment_method = models.CharField(max_length=50, default='Mobile Money')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Disbursement GHS {self.amount} for Case #{self.welfare_case.id}"
