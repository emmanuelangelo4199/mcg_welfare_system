from django.contrib import admin
from .models import ClassGroup

@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader', 'meeting_time', 'created_at')
    search_fields = ('name',)
