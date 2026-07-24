import logging
from django.db import models

logger = logging.getLogger(__name__)


def _encode_with_timeout(photo):
    """
    Directly runs get_face_encoding() with robust file stream resets
    for ImageKit, Cloudinary, or S3 backends without threading deadlocks.
    """
    from .services import get_face_encoding

    try:
        # 1. Reset stream pointer before reading image bytes
        if hasattr(photo, "file") and hasattr(photo.file, "seek"):
            try:
                photo.file.seek(0)
            except Exception:
                pass
        elif hasattr(photo, "seek"):
            try:
                photo.seek(0)
            except Exception:
                pass

        # 2. Run face detection directly on the main thread
        result = get_face_encoding(photo)

        # 3. Reset stream pointer so Django/ImageKit can upload the file
        if hasattr(photo, "file") and hasattr(photo.file, "seek"):
            try:
                photo.file.seek(0)
            except Exception:
                pass
        elif hasattr(photo, "seek"):
            try:
                photo.seek(0)
            except Exception:
                pass

        return result

    except Exception:
        logger.exception("Face encoding failed for photo %s", getattr(photo, "name", photo))
        return None


class PersonOfInterest(models.Model):
    class ThreatLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    full_name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to="persons/%Y/%m/")
    face_encoding = models.JSONField(null=True, blank=True)
    threat_level = models.CharField(
        max_length=16,
        choices=ThreatLevel.choices,
        default=ThreatLevel.LOW,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("full_name",)

    def __str__(self):
        return self.full_name

    def _photo_changed(self):
        if self.pk is None:
            return True
        try:
            old = type(self).objects.filter(pk=self.pk).only("photo").first()
            return bool(old and old.photo.name != self.photo.name)
        except Exception:
            logger.exception("Failed to check if photo changed for %s", self.pk)
            return False

    def save(self, *args, **kwargs):
        if self._photo_changed() and self.photo:
            encoding = _encode_with_timeout(self.photo)
            if encoding is not None:
                self.face_encoding = encoding.tolist() if hasattr(encoding, "tolist") else encoding
            else:
                self.face_encoding = None
        super().save(*args, **kwargs)


class PersonImage(models.Model):
    """
    Stores additional angled photos (front, left, right, top)
    and their individual encodings for accurate contrast against ESP32-CAM captures.
    """
    person = models.ForeignKey(
        PersonOfInterest,
        related_name="additional_images",
        on_delete=models.CASCADE,
    )
    photo = models.ImageField(upload_to="persons/angles/%Y/%m/")
    angle_label = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., front, left_profile, right_45_degree"
    )
    face_encoding = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.person.full_name} - {self.angle_label or 'Angle'}"

    def _photo_changed(self):
        if self.pk is None:
            return True
        try:
            old = type(self).objects.filter(pk=self.pk).only("photo").first()
            return bool(old and old.photo.name != self.photo.name)
        except Exception:
            logger.exception("Failed to check if photo changed for PersonImage %s", self.pk)
            return False

    def save(self, *args, **kwargs):
        if self._photo_changed() and self.photo:
            encoding = _encode_with_timeout(self.photo)
            if encoding is not None:
                self.face_encoding = encoding.tolist() if hasattr(encoding, "tolist") else encoding
            else:
                self.face_encoding = None
        super().save(*args, **kwargs)