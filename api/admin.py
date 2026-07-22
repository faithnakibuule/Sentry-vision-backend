# api/admin.py
from django.contrib import admin
from .models import SecuritySnapshot

@admin.register(SecuritySnapshot)
class SecuritySnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'device_id', 'created_at', 'image')
    readonly_fields = ('created_at',)