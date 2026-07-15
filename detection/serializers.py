from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import (
    DetectionLog,
    DeviceNode,
    RadarTelemetry,
    SuspectProfile,
    SystemSettings,
    UserProfile,
)


class SuspectProfileSerializer(serializers.ModelSerializer):
    """Full suspect record — used for the OLED payload and admin-facing CRUD."""

    class Meta:
        model = SuspectProfile
        fields = [
            "id",
            "name",
            "residential_area",
            "age",
            "profile_photo",
            "threat_level",
            "notes",
            "date_added",
            "date_updated",
        ]
        # face_encoding is deliberately excluded: it's an internal
        # optimization detail, not something the ESP32 or dashboard needs.
        read_only_fields = ["id", "date_added", "date_updated"]


class SuspectProfileCreateSerializer(serializers.ModelSerializer):
    """
    Used when registering a new Person of Interest. Validates that a face
    can actually be extracted from the uploaded photo before saving, so
    bad photos are rejected with a clear error rather than silently
    producing a suspect that can never be matched.
    """

    class Meta:
        model = SuspectProfile
        fields = [
            "id",
            "name",
            "residential_area",
            "age",
            "profile_photo",
            "threat_level",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate_profile_photo(self, photo):
        from .face_utils import get_face_encoding

        encoding = get_face_encoding(photo)
        photo.seek(0)  # rewind so the ImageField can still save it normally
        if encoding is None:
            raise serializers.ValidationError(
                "No face could be detected in this photo. Please upload a "
                "clear, front-facing photo of the suspect."
            )
        return photo


class RadarTelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = RadarTelemetry
        fields = [
            "id",
            "timestamp",
            "associated_detection",
            "estimated_height",
            "heart_rate",
            "movement_pattern_label",
            "zone",
        ]
        read_only_fields = ["id", "timestamp"]


class RadarTelemetryUploadSerializer(serializers.ModelSerializer):
    """
    What the RUView node actually POSTs: no `associated_detection` field —
    the view resolves that server-side by looking up the latest active
    detection, so the radar firmware doesn't need to know detection IDs.
    """

    class Meta:
        model = RadarTelemetry
        fields = ["estimated_height", "heart_rate", "movement_pattern_label", "zone"]


class DetectionLogSerializer(serializers.ModelSerializer):
    """Read serializer for the dashboard feed — nests suspect + radar data."""

    matched_suspect = SuspectProfileSerializer(read_only=True)
    radar_readings = RadarTelemetrySerializer(many=True, read_only=True)

    class Meta:
        model = DetectionLog
        fields = [
            "id",
            "timestamp",
            "captured_photo",
            "matched_suspect",
            "is_matched",
            "match_confidence",
            "status",
            "zone",
            "servo_pan_angle",
            "servo_tilt_angle",
            "device_id",
            "radar_readings",
        ]


class DetectionUploadSerializer(serializers.ModelSerializer):
    """Write serializer for the ESP32-CAM burst upload endpoint."""

    class Meta:
        model = DetectionLog
        fields = [
            "id",
            "captured_photo",
            "device_id",
            "zone",
            "servo_pan_angle",
            "servo_tilt_angle",
        ]
        read_only_fields = ["id"]


class DetectionResultResponseSerializer(serializers.Serializer):
    """
    Shape of the JSON sent back to the ESP32-CAM after a burst upload, so
    it can render the result on its local OLED. Not tied to a model —
    just documents/validates the response contract.
    """

    detection_id = serializers.IntegerField()
    is_matched = serializers.BooleanField()
    match_confidence = serializers.FloatField(allow_null=True)
    suspect = SuspectProfileSerializer(allow_null=True)
    message = serializers.CharField()


class DetectionStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Used by PATCH /api/detections/<id>/status/ — the "acknowledge alert"
    action both Admins and Security Viewers are allowed to perform. Only
    `status` is writable here; everything else about a detection
    (photo, match result) is immutable once captured.
    """

    class Meta:
        model = DetectionLog
        fields = ["status"]

    def validate_status(self, value):
        valid = {choice[0] for choice in DetectionLog.STATUS_CHOICES}
        if value not in valid:
            raise serializers.ValidationError(f"status must be one of {sorted(valid)}")
        return value


class DeviceNodeSerializer(serializers.ModelSerializer):
    """Read serializer for the Device Health page. `is_online` is computed, not stored."""

    is_online = serializers.SerializerMethodField()

    class Meta:
        model = DeviceNode
        fields = [
            "id",
            "device_id",
            "device_type",
            "label",
            "is_online",
            "last_heartbeat",
            "ip_address",
            "firmware_version",
            "sd_card_usage_percent",
            "power_status",
        ]

    def get_is_online(self, obj):
        threshold = self.context.get("offline_threshold_seconds", 60)
        return obj.is_online(offline_threshold_seconds=threshold)


class DeviceHeartbeatSerializer(serializers.ModelSerializer):
    """
    What each device POSTs every 15-30s. `device_id` is the natural key —
    get_or_create is used in the view so a device auto-registers itself
    on its very first heartbeat, no manual provisioning step required.
    """

    class Meta:
        model = DeviceNode
        fields = [
            "device_id",
            "device_type",
            "label",
            "ip_address",
            "firmware_version",
            "sd_card_usage_percent",
            "power_status",
        ]


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = [
            "face_match_tolerance",
            "motion_alert_cooldown_seconds",
            "device_offline_threshold_seconds",
            "alert_email_enabled",
            "alert_email_address",
            "alert_sms_enabled",
            "alert_sms_number",
        ]


class LoginSerializer(serializers.Serializer):
    """Validates username/password and hands back a DRF auth token + role."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        user = authenticate(
            username=attrs["username"], password=attrs["password"]
        )
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        attrs["user"] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserProfile
        fields = ["username", "role"]