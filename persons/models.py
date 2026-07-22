from django.db import models


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

    def save(self, *args, **kwargs):
        should_encode = self.pk is None
        if self.pk and not should_encode:
            old = type(self).objects.filter(pk=self.pk).only("photo").first()
            should_encode = bool(old and old.photo != self.photo)
        if should_encode and self.photo:
            from .services import get_face_encoding

            encoding = get_face_encoding(self.photo)
            self.face_encoding = encoding.tolist() if encoding is not None else None
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

    def save(self, *args, **kwargs):
        # Automatically generate face encoding for each additional angled shot
        should_encode = self.pk is None
        if self.pk and not should_encode:
            old = type(self).objects.filter(pk=self.pk).only("photo").first()
            should_encode = bool(old and old.photo != self.photo)
        if should_encode and self.photo:
            from .services import get_face_encoding

            encoding = get_face_encoding(self.photo)
            self.face_encoding = encoding.tolist() if encoding is not None else None
        super().save(*args, **kwargs)