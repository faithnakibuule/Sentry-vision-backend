from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PersonOfInterest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=255)),
                ("photo", models.ImageField(upload_to="persons/%Y/%m/")),
                ("face_encoding", models.JSONField(blank=True, null=True)),
                ("threat_level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="low", max_length=16)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("full_name",),
            },
        ),
    ]
