from rest_framework import serializers

from .models import Device


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
    sd_card_usage_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    firmware_version = serializers.CharField(required=False, allow_blank=True)
    ip_address = serializers.IPAddressField(required=False)
    is_online = serializers.BooleanField(required=False, default=True)

    def validate_device_id(self, value):
        api_key = self.context["request"].auth
        if value and value != api_key.device.device_id:
            raise serializers.ValidationError("device_id does not match the API key device.")
        return value

    def save(self):
        device = self.context["request"].auth.device
        for field in ("sd_card_usage_pct", "firmware_version", "ip_address"):
            if field in self.validated_data:
                setattr(device, field, self.validated_data[field])
        device.is_online = self.validated_data.get("is_online", True)
        from django.utils import timezone

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
