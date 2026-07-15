from django.conf import settings
from django.db import models


class Alert(models.Model):
    class Source(models.TextChoices):
        FACIAL_MATCH = "facial_match", "Facial Match"
        SUSPICIOUS_BEHAVIOR = "suspicious_behavior", "Suspicious Behavior"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    detection = models.ForeignKey(
        "detections.DetectionEvent",
        related_name="alerts",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    match_result = models.ForeignKey(
        "detections.FacialMatchResult",
        related_name="alerts",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    person = models.ForeignKey(
        "persons.PersonOfInterest",
        related_name="alerts",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    source = models.CharField(max_length=32, choices=Source.choices)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.MEDIUM)
    message = models.TextField()
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="acknowledged_alerts",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["acknowledged", "severity"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.severity}: {self.message[:60]}"
