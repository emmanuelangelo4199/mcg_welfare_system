from django.contrib import admin
from .models import Organisation, OrganisationDues

@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'president', 'meeting_schedule', 'created_at')

@admin.register(OrganisationDues)
class OrganisationDuesAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'member_name', 'amount', 'date_paid')
    list_filter = ('organisation', 'date_paid')
