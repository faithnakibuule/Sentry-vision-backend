from django.db import models
from django.utils import timezone


class RadarReading(models.Model):
    device = models.ForeignKey("devices.Device", related_name="radar_readings", on_delete=models.PROTECT)
    presence_detected = models.BooleanField(default=False)
    heart_rate_bpm = models.PositiveIntegerField(null=True, blank=True)
    height_estimate_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    movement_pattern = models.CharField(max_length=120, blank=True)
    zone = models.CharField(max_length=80, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-timestamp",)
        indexes = [
            models.Index(fields=["zone", "timestamp"]),
            models.Index(fields=["device", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.zone} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"
