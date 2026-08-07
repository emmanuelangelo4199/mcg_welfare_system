from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'gender', 'assigned_class', 'status', 'phone_number', 'created_at')
    list_filter = ('status', 'gender', 'assigned_class')
    search_fields = ('first_name', 'last_name', 'phone_number', 'email')
