from django.utils import timezone
from rest_framework import serializers

from .models import Device, DeviceStatus

# Heartbeat timeout threshold for individual sub-devices/sensors
ACTIVE_THRESHOLD_SECONDS = 15  # tune to your ESP32 heartbeat interval


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = (
            "id",
            "device_id",
            "device_type",
            "label",
            "zone",
            "location",
            "is_online",
            "last_seen",
            "sd_card_usage_pct",
            "firmware_version",
            "ip_address",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("is_online", "last_seen", "created_at", "updated_at")


class DeviceHeartbeatSerializer(serializers.Serializer):
    device_id = serializers.CharField(required=False)
    sd_card_usage_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    firmware_version = serializers.CharField(required=False, allow_blank=True)
    ip_address = serializers.IPAddressField(required=False)
    is_online = serializers.BooleanField(required=False, default=True)

    def validate_device_id(self, value):
        api_key = self.context["request"].auth
        if value and value != api_key.device.device_id:
            raise serializers.ValidationError(
                "device_id does not match the API key device."
            )
        return value

    def save(self):
        device = self.context["request"].auth.device
        for field in ("sd_card_usage_pct", "firmware_version", "ip_address"):
            if field in self.validated_data:
                setattr(device, field, self.validated_data[field])
        device.is_online = self.validated_data.get("is_online", True)
        device.last_seen = timezone.now()
        device.save(
            update_fields=[
                "sd_card_usage_pct",
                "firmware_version",
                "ip_address",
                "is_online",
                "last_seen",
                "updated_at",
            ]
        )
        return device


class DeviceStatusSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = DeviceStatus
        fields = ["device_id", "last_seen", "payload", "is_active"]
        read_only_fields = ["last_seen", "is_active"]

    def get_is_active(self, obj):
        if not obj.last_seen:
            return False
        return (timezone.now() - obj.last_seen).total_seconds() < ACTIVE_THRESHOLD_SECONDS