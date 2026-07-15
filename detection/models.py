import json
import logging

from django.db import models

logger = logging.getLogger("sentry_vision.detection")


class SuspectProfile(models.Model):
    """
    A known Person of Interest. The 128-d face encoding is computed once,
    at save time, from `profile_photo` and cached in `face_encoding` so
    that every incoming detection doesn't have to re-run feature
    extraction against every suspect photo on disk.
    """

    THREAT_LOW = "LOW"
    THREAT_MEDIUM = "MEDIUM"
    THREAT_HIGH = "HIGH"
    THREAT_CRITICAL = "CRITICAL"
    THREAT_LEVEL_CHOICES = [
        (THREAT_LOW, "Low"),
        (THREAT_MEDIUM, "Medium"),
        (THREAT_HIGH, "High"),
        (THREAT_CRITICAL, "Critical"),
    ]

    name = models.CharField(max_length=255)
    residential_area = models.CharField(max_length=255, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to="suspects/")

    # Drives the color-coded tag on the Persons of Interest gallery card
    # (e.g. CRITICAL renders red, LOW renders neutral/gray).
    threat_level = models.CharField(
        max_length=10, choices=THREAT_LEVEL_CHOICES, default=THREAT_LOW
    )
    notes = models.TextField(
        blank=True, help_text="Free-text analyst notes shown on the PoI detail view."
    )

    # 128-dimensional face_recognition encoding, stored as a JSON list of
    # floats. JSONField (not raw Binary) keeps it human-inspectable in the
    # admin/DB browser and trivially portable to Postgres later.
    face_encoding = models.JSONField(null=True, blank=True, editable=False)

    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.residential_area or 'area unknown'})"

    def set_encoding_from_photo(self):
        """
        Compute the face encoding from `profile_photo` and store it.
        Called from save(); split out so it can also be invoked manually
        (e.g. via a management command) to backfill/refresh encodings.
        """
        # Imported lazily so that `manage.py` commands unrelated to face
        # recognition (e.g. migrations) don't require dlib/face_recognition
        # to be importable just to load this module.
        from .face_utils import get_face_encoding

        if not self.profile_photo:
            self.face_encoding = None
            return

        encoding = get_face_encoding(self.profile_photo)
        if encoding is None:
            logger.warning(
                "No face detected in profile photo for suspect '%s'; "
                "face_encoding left unset. This suspect will never match.",
                self.name,
            )
            self.face_encoding = None
        else:
            self.face_encoding = json.dumps(encoding.tolist())

    def get_encoding_array(self):
        """Return the stored encoding as a numpy array, or None."""
        if not self.face_encoding:
            return None
        import numpy as np

        raw = self.face_encoding
        # JSONField may hand back a python list already, or a string
        # depending on how it was set; handle both.
        data = json.loads(raw) if isinstance(raw, str) else raw
        return np.array(data)

    def save(self, *args, **kwargs):
        # Recompute the encoding whenever this is a new record, or whenever
        # the profile photo has actually changed (avoids re-running dlib on
        # every unrelated field edit, e.g. changing `age`).
        should_encode = self.pk is None
        if not should_encode and self.pk:
            try:
                previous = SuspectProfile.objects.get(pk=self.pk)
                should_encode = previous.profile_photo != self.profile_photo
            except SuspectProfile.DoesNotExist:
                should_encode = True

        if should_encode:
            self.set_encoding_from_photo()

        super().save(*args, **kwargs)


class DetectionLog(models.Model):
    """
    A single "culprit list" entry: one burst-capture image uploaded by the
    ESP32-CAM edge node, plus the result of running it against the
    SuspectProfile face database.
    """

    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_DISMISSED = "DISMISSED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_DISMISSED, "Dismissed"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    captured_photo = models.ImageField(upload_to="detections/%Y/%m/%d/")

    matched_suspect = models.ForeignKey(
        SuspectProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="detections",
    )
    is_matched = models.BooleanField(default=False)
    match_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="0.0-1.0 confidence score, higher = more confident match.",
    )

    # Alert triage workflow for the Alerts/Incidents table. Every new
    # detection starts PENDING; a Security Viewer or Admin acknowledges it
    # via PATCH /api/detections/<id>/status/ to CONFIRMED or DISMISSED.
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING
    )

    # Where the pan-tilt servo was pointed at capture time, and which
    # named coverage zone that corresponds to — both surfaced in the
    # expanded incident row and used to place the alert on the Radar View
    # zone map.
    zone = models.CharField(max_length=50, blank=True)
    servo_pan_angle = models.FloatField(null=True, blank=True)
    servo_tilt_angle = models.FloatField(null=True, blank=True)

    # Optional metadata useful for a multi-node deployment; harmless to
    # leave null for a single edge-node setup.
    device_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        who = self.matched_suspect.name if self.matched_suspect else "Unknown"
        return f"Detection #{self.pk} @ {self.timestamp:%Y-%m-%d %H:%M:%S} -> {who}"


class RadarTelemetry(models.Model):
    """
    Non-visual telemetry pushed by the RUView Wi-Fi through-wall radar
    subsystem: height estimate, heart rate, and a classified movement
    pattern. Linked to a DetectionLog when one is active/recent so the
    dashboard can correlate "who" (vision) with "how they're behaving"
    (radar).
    """

    MOVEMENT_CHOICES = [
        ("LOITERING", "Loitering"),
        ("RUNNING", "Running"),
        ("WALKING", "Walking"),
        ("ERRATIC", "Erratic"),
        ("STATIONARY", "Stationary"),
        ("UNKNOWN", "Unknown"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    associated_detection = models.ForeignKey(
        DetectionLog,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="radar_readings",
    )

    estimated_height = models.FloatField(
        help_text="Estimated subject height in meters."
    )
    heart_rate = models.PositiveIntegerField(help_text="Beats per minute.")
    movement_pattern_label = models.CharField(
        max_length=20, choices=MOVEMENT_CHOICES, default="UNKNOWN"
    )

    # Named coverage zone the radar node placed this reading in (e.g.
    # "front_door", "driveway"). Lets the Radar View overlay presence /
    # heart-rate / movement directly onto the same zone the camera used,
    # without needing raw x/y coordinates from a single fixed radar node.
    zone = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Radar Telemetry (RUView)"
        verbose_name_plural = "Radar Telemetry (RUView)"

    def __str__(self):
        return (
            f"RUView @ {self.timestamp:%Y-%m-%d %H:%M:%S} - "
            f"{self.movement_pattern_label}, {self.heart_rate}bpm"
        )


class DeviceNode(models.Model):
    """
    One physical piece of edge hardware (an ESP32-CAM, the Arduino Uno
    driving the servos/sensors, or a RUView radar node). Populated and
    kept fresh by each device calling POST /api/devices/heartbeat/ on a
    regular interval (e.g. every 15-30s). Powers the Device Health page.
    """

    TYPE_ESP32_CAM = "ESP32_CAM"
    TYPE_ARDUINO_UNO = "ARDUINO_UNO"
    TYPE_RUVIEW_RADAR = "RUVIEW_RADAR"
    DEVICE_TYPE_CHOICES = [
        (TYPE_ESP32_CAM, "ESP32-CAM"),
        (TYPE_ARDUINO_UNO, "Arduino Uno"),
        (TYPE_RUVIEW_RADAR, "RUView Radar Node"),
    ]

    POWER_MAINS = "MAINS"
    POWER_BATTERY = "BATTERY"
    POWER_LOW_BATTERY = "LOW_BATTERY"
    POWER_UNKNOWN = "UNKNOWN"
    POWER_STATUS_CHOICES = [
        (POWER_MAINS, "Mains Powered"),
        (POWER_BATTERY, "On Battery"),
        (POWER_LOW_BATTERY, "Low Battery"),
        (POWER_UNKNOWN, "Unknown"),
    ]

    device_id = models.CharField(
        max_length=100, unique=True, help_text="Stable hardware identifier, e.g. MAC address."
    )
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES)
    label = models.CharField(
        max_length=100, blank=True, help_text="Human-friendly name, e.g. 'Front Door Cam'."
    )

    last_heartbeat = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    firmware_version = models.CharField(max_length=50, blank=True)

    # Only meaningful for the ESP32-CAM node, but harmless/null elsewhere.
    sd_card_usage_percent = models.FloatField(null=True, blank=True)
    power_status = models.CharField(
        max_length=15, choices=POWER_STATUS_CHOICES, default=POWER_UNKNOWN
    )

    class Meta:
        ordering = ["device_type", "device_id"]

    def __str__(self):
        return f"{self.label or self.device_id} ({self.get_device_type_display()})"

    def is_online(self, offline_threshold_seconds=60):
        """
        A device is considered online if it heartbeat within the
        configured threshold (see SystemSettings.device_offline_threshold_seconds).
        Computed on read rather than stored, so a device that silently
        drops offline is correctly reported without needing a background
        job to flip a stale flag.
        """
        if not self.last_heartbeat:
            return False
        from django.utils import timezone

        age = (timezone.now() - self.last_heartbeat).total_seconds()
        return age <= offline_threshold_seconds


class SystemSettings(models.Model):
    """
    Singleton row (always pk=1) holding the tunables exposed on the
    Settings page: detection sensitivity, alert channels, and the
    device-offline threshold used by DeviceNode.is_online().
    """

    face_match_tolerance = models.FloatField(
        default=0.6,
        help_text="Lower = stricter face match. Mirrors face_utils.DEFAULT_TOLERANCE.",
    )
    motion_alert_cooldown_seconds = models.PositiveIntegerField(
        default=30,
        help_text="Minimum gap between motion-triggered alerts to avoid spamming.",
    )
    device_offline_threshold_seconds = models.PositiveIntegerField(
        default=60,
        help_text="A device with no heartbeat in this window is shown as OFFLINE.",
    )

    alert_email_enabled = models.BooleanField(default=False)
    alert_email_address = models.EmailField(blank=True)
    alert_sms_enabled = models.BooleanField(default=False)
    alert_sms_number = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "SENTRY-VISION System Settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton — there is only ever one settings row
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # singleton is never deleted

    @classmethod
    def load(cls):
        """Get-or-create the one settings row. Always safe to call."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class UserProfile(models.Model):
    """
    Extends Django's built-in auth.User with the two SENTRY-VISION roles:
      - ADMIN: full CRUD (manage suspects, edit settings, everything)
      - VIEWER: read-only + can acknowledge alerts (confirm/dismiss)
    Auto-created for every new User via a signal in detection/signals.py.
    """

    ROLE_ADMIN = "ADMIN"
    ROLE_VIEWER = "VIEWER"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_VIEWER, "Security Viewer"),
    ]

    user = models.OneToOneField(
        "auth.User", on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_VIEWER)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"