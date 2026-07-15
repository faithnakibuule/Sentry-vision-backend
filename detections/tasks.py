import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from alerts.models import Alert
from persons.models import PersonOfInterest
from persons.services import compare_encoding, get_face_encoding

from .models import DetectionEvent, FacialMatchResult

logger = logging.getLogger(__name__)


THREAT_TO_SEVERITY = {
    "low": Alert.Severity.LOW,
    "medium": Alert.Severity.HIGH,
    "high": Alert.Severity.CRITICAL,
}


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 2, "countdown": 5})
def process_detection_event(self, detection_id):
    detection = DetectionEvent.objects.select_related("device").get(id=detection_id)
    result, _ = FacialMatchResult.objects.get_or_create(detection=detection)

    try:
        unknown_encoding = get_face_encoding(detection.image)
        if unknown_encoding is None:
            result.status = FacialMatchResult.Status.UNMATCHED
            result.error_message = "No face detected in image."
            result.save(update_fields=["status", "error_message", "updated_at"])
            _maybe_create_suspicious_alert(detection)
            detection.processing_status = DetectionEvent.ProcessingStatus.PROCESSED
            detection.save(update_fields=["processing_status"])
            return result.id

        person, confidence, distance = compare_encoding(
            unknown_encoding,
            PersonOfInterest.objects.exclude(face_encoding__isnull=True),
            settings.FACE_MATCH_TOLERANCE,
        )

        with transaction.atomic():
            result.person = person
            result.confidence_score = confidence
            result.face_distance = distance
            result.status = FacialMatchResult.Status.MATCHED if person else FacialMatchResult.Status.UNMATCHED
            result.error_message = ""
            result.save()

            detection.processing_status = DetectionEvent.ProcessingStatus.PROCESSED
            detection.save(update_fields=["processing_status"])

            if person:
                Alert.objects.create(
                    detection=detection,
                    match_result=result,
                    person=person,
                    source=Alert.Source.FACIAL_MATCH,
                    severity=THREAT_TO_SEVERITY.get(person.threat_level, Alert.Severity.MEDIUM),
                    message=f"Facial match detected for {person.full_name}.",
                )
            else:
                _maybe_create_suspicious_alert(detection)
        return result.id
    except Exception as exc:
        logger.exception("Facial recognition failed for detection %s", detection_id)
        result.status = FacialMatchResult.Status.FAILED
        result.error_message = str(exc)
        result.save(update_fields=["status", "error_message", "updated_at"])
        detection.processing_status = DetectionEvent.ProcessingStatus.FAILED
        detection.save(update_fields=["processing_status"])
        raise


def _maybe_create_suspicious_alert(detection):
    window_start = detection.timestamp - timezone.timedelta(seconds=settings.SUSPICIOUS_WINDOW_SECONDS)
    repeated = DetectionEvent.objects.filter(
        zone=detection.zone,
        timestamp__gte=window_start,
        timestamp__lte=detection.timestamp,
    ).count()
    if repeated >= settings.SUSPICIOUS_DETECTION_COUNT:
        Alert.objects.get_or_create(
            detection=detection,
            source=Alert.Source.SUSPICIOUS_BEHAVIOR,
            defaults={
                "severity": Alert.Severity.MEDIUM,
                "message": f"Repeated activity detected in {detection.zone}.",
            },
        )
