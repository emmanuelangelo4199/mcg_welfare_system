from django.db import models
from django.conf import settings

class IncomeLedger(models.Model):
    CATEGORY_CHOICES = [
        ('TITHE', 'Tithe'),
        ('OFFERING', 'Sunday Offering'),
        ('WELFARE', 'Welfare Dues'),
        ('HARVEST', 'Annual Harvest'),
        ('DONATION', 'Donation / Special Offering'),
        ('OTHER', 'Other Income'),
    ]

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()} - GHS {self.amount} ({self.date})"

class ExpenseLedger(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_expenses')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - GHS {self.amount} ({self.get_status_display()})"

class Budget(models.Model):
    fiscal_year = models.IntegerField()
    category = models.CharField(max_length=100)
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.fiscal_year} Budget: {self.category} - GHS {self.allocated_amount}"
