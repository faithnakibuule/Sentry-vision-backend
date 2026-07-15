from django.db.models.signals import post_save
from django.dispatch import receiver

from .broadcast import broadcast_alert_event
from .models import Alert
from .serializers import AlertSerializer


@receiver(post_save, sender=Alert)
def push_new_alert(sender, instance, created, **kwargs):
    if created:
        broadcast_alert_event("alert.created", AlertSerializer(instance).data)
