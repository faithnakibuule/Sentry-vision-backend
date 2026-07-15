from rest_framework import serializers

from .models import SystemLog


class SystemLogSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = SystemLog
        fields = ("id", "device", "device_id", "level", "message", "metadata", "timestamp", "created_at")
        read_only_fields = ("device", "created_at")

    def validate_device_id(self, value):
        api_key = self.context["request"].auth
        if value and value != api_key.device.device_id:
            raise serializers.ValidationError("device_id does not match the API key device.")
        return value

    def create(self, validated_data):
        validated_data.pop("device_id", None)
        device = getattr(self.context["request"].auth, "device", None)
        return SystemLog.objects.create(device=device, **validated_data)
