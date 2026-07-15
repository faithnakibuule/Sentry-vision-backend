from rest_framework import serializers

from .models import RadarReading


class RadarReadingSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = RadarReading
        fields = (
            "id",
            "device",
            "device_id",
            "presence_detected",
            "heart_rate_bpm",
            "height_estimate_cm",
            "movement_pattern",
            "zone",
            "timestamp",
            "created_at",
        )
        read_only_fields = ("device", "zone", "created_at")

    def validate_device_id(self, value):
        api_key = self.context["request"].auth
        if value and value != api_key.device.device_id:
            raise serializers.ValidationError("device_id does not match the API key device.")
        return value

    def create(self, validated_data):
        validated_data.pop("device_id", None)
        device = self.context["request"].auth.device
        return RadarReading.objects.create(device=device, zone=device.zone, **validated_data)
