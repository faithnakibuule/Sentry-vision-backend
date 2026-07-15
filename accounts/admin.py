from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SentryVisionUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("SENTRY-VISION", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = UserAdmin.list_filter + ("role",)
