from django.db import transaction
from rest_framework import serializers

from .models import DetectionEvent, FacialMatchResult


class FacialMatchResultSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.full_name", read_only=True)

    class Meta:
        model = FacialMatchResult
        fields = (
            "id",
            "status",
            "person",
            "person_name",
            "confidence_score",
            "face_distance",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DetectionEventSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(write_only=True, required=False)
    match_result = FacialMatchResultSerializer(read_only=True)

    class Meta:
        model = DetectionEvent
        fields = (
            "id",
            "device",
            "device_id",
            "image",
            "trigger_source",
            "servo_angle",
            "distance_cm",
            "zone",
            "timestamp",
            "processing_status",
            "match_result",
            "created_at",
        )
        read_only_fields = ("device", "zone", "processing_status", "match_result", "created_at")

    def validate_device_id(self, value):
        api_key = self.context["request"].auth
        if value and value != api_key.device.device_id:
            raise serializers.ValidationError("device_id does not match the API key device.")
        return value

    def create(self, validated_data):
        validated_data.pop("device_id", None)
        device = self.context["request"].auth.device
        event = DetectionEvent.objects.create(device=device, zone=device.zone, **validated_data)
        FacialMatchResult.objects.create(detection=event)

        from .tasks import process_detection_event

        transaction.on_commit(lambda: process_detection_event.delay(event.id))
        return event
