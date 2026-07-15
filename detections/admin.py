from django.contrib import admin

from .models import DetectionEvent, FacialMatchResult


@admin.register(DetectionEvent)
class DetectionEventAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "trigger_source", "zone", "timestamp", "processing_status")
    list_filter = ("trigger_source", "processing_status", "zone")
    search_fields = ("device__device_id", "zone")


@admin.register(FacialMatchResult)
class FacialMatchResultAdmin(admin.ModelAdmin):
    list_display = ("detection", "status", "person", "confidence_score", "created_at")
    list_filter = ("status",)
