import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("devices", "0001_initial"),
        ("persons", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DetectionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="detections/%Y/%m/%d/")),
                ("trigger_source", models.CharField(choices=[("motion", "Motion"), ("ultrasonic", "Ultrasonic"), ("radar", "Radar"), ("manual", "Manual")], max_length=32)),
                ("servo_angle", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("distance_cm", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("zone", models.CharField(db_index=True, max_length=80)),
                ("timestamp", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("processing_status", models.CharField(choices=[("pending", "Pending"), ("processed", "Processed"), ("failed", "Failed")], default="pending", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="detections", to="devices.device")),
            ],
            options={
                "ordering": ("-timestamp",),
                "indexes": [models.Index(fields=["zone", "timestamp"], name="detections_zone_timestamp_idx"), models.Index(fields=["device", "timestamp"], name="detections_device_timestamp_idx")],
            },
        ),
        migrations.CreateModel(
            name="FacialMatchResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("matched", "Matched"), ("unmatched", "Unmatched"), ("failed", "Failed")], default="pending", max_length=16)),
                ("confidence_score", models.FloatField(blank=True, null=True)),
                ("face_distance", models.FloatField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("detection", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="match_result", to="detections.detectionevent")),
                ("person", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="match_results", to="persons.personofinterest")),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
    ]
