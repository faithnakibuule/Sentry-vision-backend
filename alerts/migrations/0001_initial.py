import django.conf
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("detections", "0001_initial"),
        ("persons", "0001_initial"),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Alert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(choices=[("facial_match", "Facial Match"), ("suspicious_behavior", "Suspicious Behavior")], max_length=32)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="medium", max_length=16)),
                ("message", models.TextField()),
                ("acknowledged", models.BooleanField(default=False)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("acknowledged_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acknowledged_alerts", to=django.conf.settings.AUTH_USER_MODEL)),
                ("detection", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alerts", to="detections.detectionevent")),
                ("match_result", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alerts", to="detections.facialmatchresult")),
                ("person", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alerts", to="persons.personofinterest")),
            ],
            options={
                "ordering": ("-created_at",),
                "indexes": [models.Index(fields=["acknowledged", "severity"], name="alerts_ack_severity_idx"), models.Index(fields=["created_at"], name="alerts_created_at_idx")],
            },
        ),
    ]
