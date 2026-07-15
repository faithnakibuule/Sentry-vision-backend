from django.db import models
from django.utils import timezone


class DetectionEvent(models.Model):
    class TriggerSource(models.TextChoices):
        MOTION = "motion", "Motion"
        ULTRASONIC = "ultrasonic", "Ultrasonic"
        RADAR = "radar", "Radar"
        MANUAL = "manual", "Manual"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    device = models.ForeignKey("devices.Device", related_name="detections", on_delete=models.PROTECT)
    image = models.ImageField(upload_to="detections/%Y/%m/%d/")
    trigger_source = models.CharField(max_length=32, choices=TriggerSource.choices)
    servo_angle = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    distance_cm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    zone = models.CharField(max_length=80, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    processing_status = models.CharField(
        max_length=16,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-timestamp",)
        indexes = [
            models.Index(fields=["zone", "timestamp"]),
            models.Index(fields=["device", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.device} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"


class FacialMatchResult(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        MATCHED = "matched", "Matched"
        UNMATCHED = "unmatched", "Unmatched"
        FAILED = "failed", "Failed"

    detection = models.OneToOneField(DetectionEvent, related_name="match_result", on_delete=models.CASCADE)
    person = models.ForeignKey(
        "persons.PersonOfInterest",
        related_name="match_results",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    confidence_score = models.FloatField(null=True, blank=True)
    face_distance = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.detection_id}: {self.status}"
