import logging

from django.db import models

logger = logging.getLogger(__name__)


class PersonOfInterest(models.Model):
    class ThreatLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    full_name = models.CharField(max_length=255)
    # Primary / Default profile photo
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
        """
        Returns True if this is a new instance, or if the photo field
        has changed compared to what's currently stored in the database.
        Wrapped in try/except so a storage-backend hiccup here can never
        block the save.
        """
        if self.pk is None:
            return True
        try:
            old = type(self).objects.filter(pk=self.pk).only("photo").first()
            return bool(old and old.photo.name != self.photo.name)
        except Exception:
            logger.exception("Failed to check if photo changed for %s", self.pk)
            # If we can't tell, err on the side of NOT re-encoding, since
            # this comparison firing on every save is what risks a hang.
            return False

    def save(self, *args, **kwargs):
        if self._photo_changed() and self.photo:
            from .services import get_face_encoding

            try:
                encoding = get_face_encoding(self.photo)
                self.face_encoding = encoding.tolist() if encoding is not None else None
            except Exception:
                # Never let a face-encoding failure block saving the record.
                logger.exception("Face encoding failed for PersonOfInterest %s", self.pk)
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
        # Automatically generate face encoding for each additional angled shot
        if self._photo_changed() and self.photo:
            from .services import get_face_encoding

            try:
                encoding = get_face_encoding(self.photo)
                self.face_encoding = encoding.tolist() if encoding is not None else None
            except Exception:
                logger.exception("Face encoding failed for PersonImage %s", self.pk)
                self.face_encoding = None
        super().save(*args, **kwargs)