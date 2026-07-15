from django.contrib import admin

from .models import RadarReading


@admin.register(RadarReading)
class RadarReadingAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "zone", "presence_detected", "heart_rate_bpm", "timestamp")
    list_filter = ("presence_detected", "zone", "movement_pattern")
    search_fields = ("device__device_id", "zone", "movement_pattern")
