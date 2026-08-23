from django.contrib import admin
from .models import Organisation, OrganisationMembership, OrganisationDues, OrganisationMeeting


class OrganisationMembershipInline(admin.TabularInline):
    model = OrganisationMembership
    extra = 1


class OrganisationDuesInline(admin.TabularInline):
    model = OrganisationDues
    extra = 0
    readonly_fields = ('created_at',)


class OrganisationMeetingInline(admin.TabularInline):
    model = OrganisationMeeting
    extra = 1


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'president', 'secretary', 'treasurer', 'meeting_schedule', 'location', 'is_active', 'member_count', 'total_dues', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'meeting_schedule', 'location')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrganisationMembershipInline, OrganisationDuesInline, OrganisationMeetingInline]
    ordering = ('name',)


@admin.register(OrganisationMembership)
class OrganisationMembershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'organisation', 'member', 'role', 'joined_date', 'is_active')
    list_filter = ('role', 'is_active', 'organisation')
    search_fields = ('member__first_name', 'member__last_name', 'organisation__name')


@admin.register(OrganisationDues)
class OrganisationDuesAdmin(admin.ModelAdmin):
    list_display = ('id', 'organisation', 'member', 'member_name', 'amount', 'payment_method', 'date_paid', 'receipt_number', 'recorded_by', 'created_at')
    list_filter = ('organisation', 'payment_method', 'date_paid')
    search_fields = ('member_name', 'organisation__name', 'receipt_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(OrganisationMeeting)
class OrganisationMeetingAdmin(admin.ModelAdmin):
    list_display = ('id', 'organisation', 'date', 'topic', 'venue', 'created_by', 'created_at')
    list_filter = ('date', 'organisation')
    search_fields = ('organisation__name', 'topic')