from django.contrib import admin

from .models import (
    DetectionLog,
    DeviceNode,
    RadarTelemetry,
    SuspectProfile,
    SystemSettings,
    UserProfile,
)


@admin.register(SuspectProfile)
class SuspectProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name", "residential_area", "age", "threat_level", "has_encoding", "date_added"
    )
    list_filter = ("threat_level",)
    search_fields = ("name", "residential_area")
    readonly_fields = ("date_added", "date_updated")

    @admin.display(boolean=True, description="Encoding cached")
    def has_encoding(self, obj):
        return obj.face_encoding is not None


class RadarTelemetryInline(admin.TabularInline):
    model = RadarTelemetry
    extra = 0
    fields = ("timestamp", "estimated_height", "heart_rate", "movement_pattern_label")
    readonly_fields = ("timestamp",)


@admin.register(DetectionLog)
class DetectionLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "timestamp", "matched_suspect", "is_matched", "status", "zone", "match_confidence"
    )
    list_filter = ("is_matched", "status", "zone")
    inlines = [RadarTelemetryInline]


@admin.register(RadarTelemetry)
class RadarTelemetryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "timestamp",
        "associated_detection",
        "estimated_height",
        "heart_rate",
        "movement_pattern_label",
        "zone",
    )
    list_filter = ("movement_pattern_label", "zone")


@admin.register(DeviceNode)
class DeviceNodeAdmin(admin.ModelAdmin):
    list_display = (
        "device_id", "device_type", "label", "power_status",
        "sd_card_usage_percent", "last_heartbeat",
    )
    list_filter = ("device_type", "power_status")


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Singleton — block adding a second row from the admin UI.
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)