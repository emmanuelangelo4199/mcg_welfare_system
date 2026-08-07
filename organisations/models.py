from django.db import models
from django.conf import settings

class Organisation(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    president = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='led_organisations'
    )
    meeting_schedule = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class OrganisationDues(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='dues')
    member_name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateField()
    remarks = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.organisation.name} Dues - {self.member_name} (GHS {self.amount})"
