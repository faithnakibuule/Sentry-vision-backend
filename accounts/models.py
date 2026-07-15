from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        VIEWER = "viewer", "Viewer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)

    @property
    def is_sentry_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN
