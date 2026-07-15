from django.contrib import admin

from .models import Device, DeviceAPIKey


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_id", "device_type", "zone", "is_online", "last_seen")
    list_filter = ("device_type", "is_online", "zone")
    search_fields = ("device_id", "label", "zone", "location")


@admin.register(DeviceAPIKey)
class DeviceAPIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "device", "key_prefix", "is_active", "created_at", "last_used_at")
    list_filter = ("is_active", "created_at")
    readonly_fields = ("key_prefix", "key_hash", "created_at", "last_used_at")
