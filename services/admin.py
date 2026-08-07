from django.contrib import admin
from .models import ChurchService

@admin.register(ChurchService)
class ChurchServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'service_date', 'start_time', 'preacher', 'theme')
