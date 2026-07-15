from django.db import models
from django.utils import timezone


class SystemLog(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARN = "warn", "Warning"
        ERROR = "error", "Error"

    device = models.ForeignKey("devices.Device", related_name="logs", null=True, blank=True, on_delete=models.SET_NULL)
    level = models.CharField(max_length=16, choices=Level.choices)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-timestamp",)
        indexes = [models.Index(fields=["level", "timestamp"])]

    def __str__(self):
        return f"{self.level}: {self.message[:60]}"
