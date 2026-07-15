from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from alerts.models import Alert
from detections.models import DetectionEvent, FacialMatchResult
from devices.models import Device
from persons.models import PersonOfInterest
from radar.models import RadarReading


def build_placeholder_image(name="person.png"):
    image = Image.new("RGB", (128, 128), color=(60, 70, 85))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=name)


class Command(BaseCommand):
    help = "Seed demo data for Sentry Vision backend"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@sentry-vision.local",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin_user.set_password("Password123!")
            admin_user.save()
        else:
            updated = False
            if not admin_user.is_staff:
                admin_user.is_staff = True
                updated = True
            if not admin_user.is_superuser:
                admin_user.is_superuser = True
                updated = True
            if not admin_user.check_password("Password123!"):
                admin_user.set_password("Password123!")
                updated = True
            if updated:
                admin_user.save()

        devices = [
            {
                "device_id": "CAM-01",
                "device_type": Device.Type.ESP32_CAM,
                "label": "North Gate CAM",
                "zone": "North Gate",
                "location": "North Gate perimeter",
                "is_online": True,
                "sd_card_usage_pct": 68,
                "firmware_version": "v1.4.2",
                "ip_address": "192.168.1.21",
            },
            {
                "device_id": "CAM-02",
                "device_type": Device.Type.ESP32_CAM,
                "label": "Loading Bay CAM",
                "zone": "Loading Bay",
                "location": "Warehouse entry",
                "is_online": True,
                "sd_card_usage_pct": 54,
                "firmware_version": "v1.4.2",
                "ip_address": "192.168.1.22",
            },
            {
                "device_id": "RAD-01",
                "device_type": Device.Type.RUVIEW_RADAR,
                "label": "Server Hall Radar",
                "zone": "Server Hall",
                "location": "Server Hall conduit",
                "is_online": True,
                "sd_card_usage_pct": None,
                "firmware_version": "v2.1.0",
                "ip_address": "192.168.1.31",
            },
        ]

        device_objs = []
        for device_data in devices:
            device, _ = Device.objects.get_or_create(device_id=device_data["device_id"], defaults=device_data)
            device_objs.append(device)

        persons = [
            {
                "full_name": "Marcel Dane",
                "threat_level": PersonOfInterest.ThreatLevel.HIGH,
                "notes": "Former contractor. Escalate immediately if detected near server hall.",
            },
            {
                "full_name": "Talia Renn",
                "threat_level": PersonOfInterest.ThreatLevel.MEDIUM,
                "notes": "Monitor only. Requires supervisor confirmation before escalation.",
            },
        ]

        person_objs = []
        for person_data in persons:
            person, _ = PersonOfInterest.objects.get_or_create(
                full_name=person_data["full_name"],
                defaults={
                    "face_encoding": [],
                    **person_data,
                },
            )
            person_objs.append(person)

        now = timezone.now()
        detections = [
            {
                "device": device_objs[0],
                "trigger_source": DetectionEvent.TriggerSource.MOTION,
                "servo_angle": 118.0,
                "distance_cm": 230.5,
                "zone": "North Gate",
                "timestamp": now - timezone.timedelta(minutes=2),
                "processing_status": DetectionEvent.ProcessingStatus.PROCESSED,
            },
            {
                "device": device_objs[1],
                "trigger_source": DetectionEvent.TriggerSource.RADAR,
                "servo_angle": 64.0,
                "distance_cm": 145.9,
                "zone": "Loading Bay",
                "timestamp": now - timezone.timedelta(minutes=6),
                "processing_status": DetectionEvent.ProcessingStatus.PROCESSED,
            },
            {
                "device": device_objs[2],
                "trigger_source": DetectionEvent.TriggerSource.ULTRASONIC,
                "servo_angle": 91.0,
                "distance_cm": 122.0,
                "zone": "Server Hall",
                "timestamp": now - timezone.timedelta(minutes=11),
                "processing_status": DetectionEvent.ProcessingStatus.PROCESSED,
            },
        ]

        detection_objs = []
        for detection_data in detections:
            detection, _ = DetectionEvent.objects.get_or_create(
                device=detection_data["device"],
                timestamp=detection_data["timestamp"],
                defaults=detection_data,
            )
            detection_objs.append(detection)

        for detection, person in zip(detection_objs, person_objs):
            FacialMatchResult.objects.get_or_create(
                detection=detection,
                defaults={
                    "person": person,
                    "status": FacialMatchResult.Status.MATCHED,
                    "confidence_score": 0.94,
                    "face_distance": 0.06,
                },
            )

        alerts_data = [
            {
                "detection": detection_objs[0],
                "match_result": FacialMatchResult.objects.filter(detection=detection_objs[0]).first(),
                "person": person_objs[0],
                "source": Alert.Source.FACIAL_MATCH,
                "severity": Alert.Severity.CRITICAL,
                "message": "POI match at North Gate",
                "acknowledged": False,
            },
            {
                "detection": detection_objs[1],
                "match_result": FacialMatchResult.objects.filter(detection=detection_objs[1]).first(),
                "source": Alert.Source.SUSPICIOUS_BEHAVIOR,
                "severity": Alert.Severity.HIGH,
                "message": "Motion beyond perimeter line",
                "acknowledged": False,
            },
            {
                "detection": detection_objs[2],
                "match_result": FacialMatchResult.objects.filter(detection=detection_objs[2]).first(),
                "person": person_objs[1],
                "source": Alert.Source.FACIAL_MATCH,
                "severity": Alert.Severity.MEDIUM,
                "message": "Person of interest detected in server hall",
                "acknowledged": True,
                "acknowledged_by": admin_user,
                "acknowledged_at": now - timezone.timedelta(minutes=5),
            },
        ]

        for alert_data in alerts_data:
            Alert.objects.get_or_create(
                detection=alert_data.get("detection"),
                message=alert_data["message"],
                defaults=alert_data,
            )

        radar_readings = [
            {
                "device": device_objs[2],
                "presence_detected": True,
                "heart_rate_bpm": 88,
                "height_estimate_cm": 176.4,
                "movement_pattern": "steady",
                "zone": "Server Hall",
                "timestamp": now - timezone.timedelta(minutes=3),
            },
            {
                "device": device_objs[2],
                "presence_detected": False,
                "heart_rate_bpm": None,
                "height_estimate_cm": None,
                "movement_pattern": "none",
                "zone": "East Corridor",
                "timestamp": now - timezone.timedelta(minutes=8),
            },
        ]

        for reading_data in radar_readings:
            RadarReading.objects.get_or_create(
                device=reading_data["device"],
                timestamp=reading_data["timestamp"],
                defaults=reading_data,
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
