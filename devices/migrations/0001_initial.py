import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Device",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_id", models.CharField(max_length=120, unique=True)),
                ("device_type", models.CharField(choices=[("arduino_uno", "Arduino Uno"), ("esp32_cam", "ESP32-CAM"), ("ruview_radar", "RUView Radar")], max_length=32)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("zone", models.CharField(db_index=True, max_length=80)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("is_online", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("last_seen", models.DateTimeField(blank=True, null=True)),
                ("sd_card_usage_pct", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("firmware_version", models.CharField(blank=True, max_length=80)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("device_type", "zone", "device_id"),
            },
        ),
        migrations.CreateModel(
            name="DeviceAPIKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("key_prefix", models.CharField(db_index=True, max_length=8)),
                ("key_hash", models.CharField(max_length=256)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_keys", to="devices.device")),
            ],
            options={
                "ordering": ("device", "name"),
                "unique_together": {("device", "name")},
            },
        ),
    ]
