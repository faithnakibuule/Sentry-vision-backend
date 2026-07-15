"""
signals.py
==========
One job: whenever a new Django `auth.User` is created (e.g. via
`createsuperuser` or the future user-management UI), automatically attach
a `UserProfile` so `request.user.profile.role` is always safe to read in
permission checks — no need to remember to create it manually.

New users default to VIEWER (least privilege). Promote to ADMIN via
/admin/ or the Django shell:
    u = User.objects.get(username="...")
    u.profile.role = "ADMIN"
    u.profile.save()
"""
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # If a profile is somehow missing on an existing user (e.g. one
        # created before this signal existed), backfill it rather than
        # erroring out on the next permission check.
        UserProfile.objects.get_or_create(user=instance)