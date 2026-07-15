import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class Device(models.Model):
    class Type(models.TextChoices):
        ARDUINO_UNO = "arduino_uno", "Arduino Uno"
        ESP32_CAM = "esp32_cam", "ESP32-CAM"
        RUVIEW_RADAR = "ruview_radar", "RUView Radar"

    device_id = models.CharField(max_length=120, unique=True)
    device_type = models.CharField(max_length=32, choices=Type.choices)
    label = models.CharField(max_length=120, blank=True)
    zone = models.CharField(max_length=80, db_index=True)
    location = models.CharField(max_length=255, blank=True)
    is_online = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    sd_card_usage_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    firmware_version = models.CharField(max_length=80, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("device_type", "zone", "device_id")

    def __str__(self):
        return self.label or self.device_id

    def mark_seen(self):
        self.is_online = True
        self.last_seen = timezone.now()
        self.save(update_fields=["is_online", "last_seen", "updated_at"])


class DeviceAPIKey(models.Model):
    device = models.ForeignKey(Device, related_name="api_keys", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    key_prefix = models.CharField(max_length=8, db_index=True)
    key_hash = models.CharField(max_length=256)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("device", "name")
        ordering = ("device", "name")

    def __str__(self):
        return f"{self.device} - {self.name}"

    @classmethod
    def issue_key(cls, device, name="default"):
        raw_key = secrets.token_urlsafe(32)
        obj = cls.objects.create(
            device=device,
            name=name,
            key_prefix=raw_key[:8],
            key_hash=make_password(raw_key),
        )
        return obj, raw_key

    def matches(self, raw_key):
        return check_password(raw_key, self.key_hash)
