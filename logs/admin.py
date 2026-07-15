from django.contrib import admin

from .models import SystemLog


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("id", "level", "device", "message", "timestamp")
    list_filter = ("level", "timestamp")
    search_fields = ("message", "device__device_id")
