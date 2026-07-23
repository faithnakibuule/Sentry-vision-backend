import uuid
from django.db import models


class SecuritySnapshot(models.Model):
    """
    Stores permanent snapshot images captured by the ESP32-CAM 
    when the hardware sensor trigger pin (GPIO 12) is pulled HIGH.
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    device_id = models.CharField(
        max_length=50, 
        default="ESP32_AI_CAM",
        help_text="Identifier for the ESP32 unit sending the frame"
    )
    image = models.ImageField(
        upload_to='snapshots/%Y/%m/%d/',
        help_text="Path to stored JPEG snapshot on media disk"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the snapshot was received and saved"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Security Snapshot"
        verbose_name_plural = "Security Snapshots"

    def __str__(self):
        return f"Snapshot {self.id} from {self.device_id} at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"