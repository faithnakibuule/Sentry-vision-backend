from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "severity", "source", "person", "acknowledged", "created_at")
    list_filter = ("severity", "source", "acknowledged")
    search_fields = ("message", "person__full_name", "detection__zone")
