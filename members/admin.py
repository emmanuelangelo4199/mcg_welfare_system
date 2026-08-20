from django.contrib import admin

from .models import Member, MemberRegularisation, MemberTransfer


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'gender', 'assigned_class', 'status', 'phone_number', 'created_at')
    list_filter = ('status', 'gender', 'assigned_class')
    search_fields = ('first_name', 'last_name', 'phone_number', 'email')


@admin.register(MemberRegularisation)
class MemberRegularisationAdmin(admin.ModelAdmin):
    list_display = ('member', 'decision', 'approval_date', 'assigned_class', 'processed_by')
    list_filter = ('decision', 'approval_date', 'assigned_class')
    search_fields = ('member__first_name', 'member__last_name', 'meeting_reference')
    autocomplete_fields = ('member', 'assigned_class', 'processed_by')

admin.site.register(MemberTransfer)