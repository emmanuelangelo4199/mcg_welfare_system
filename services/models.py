from django.db import models

class ChurchService(models.Model):
    title = models.CharField(max_length=200)
    service_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    preacher = models.CharField(max_length=150, blank=True, null=True)
    liturgist = models.CharField(max_length=150, blank=True, null=True)
    theme = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.service_date})"
