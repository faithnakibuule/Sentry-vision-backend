from django.apps import AppConfig


class DetectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "detection"
    verbose_name = "SENTRY-VISION Detection Engine"

    def ready(self):
        # Registers the post_save->UserProfile signal. Must be imported
        # here (not at module top-level) so Django's app registry is
        # fully loaded before the signal's model imports run.
        from . import signals  # noqa: F401