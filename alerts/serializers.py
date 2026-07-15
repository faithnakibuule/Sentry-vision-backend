from django.utils import timezone
from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    zone = serializers.CharField(source="detection.zone", read_only=True)
    acknowledged_by_username = serializers.CharField(source="acknowledged_by.username", read_only=True)

    class Meta:
        model = Alert
        fields = (
            "id",
            "detection",
            "match_result",
            "person",
            "person_name",
            "zone",
            "source",
            "severity",
            "message",
            "acknowledged",
            "acknowledged_by",
            "acknowledged_by_username",
            "acknowledged_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AlertAcknowledgeSerializer(serializers.ModelSerializer):
    acknowledged = serializers.BooleanField(default=True)

    class Meta:
        model = Alert
        fields = ("acknowledged",)

    def update(self, instance, validated_data):
        instance.acknowledged = validated_data.get("acknowledged", True)
        if instance.acknowledged:
            instance.acknowledged_by = self.context["request"].user
            instance.acknowledged_at = timezone.now()
        else:
            instance.acknowledged_by = None
            instance.acknowledged_at = None
        instance.save(update_fields=["acknowledged", "acknowledged_by", "acknowledged_at", "updated_at"])
        return instance
