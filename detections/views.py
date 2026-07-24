import datetime
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import mixins, viewsets, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

# Preserving your exact architectural imports
from accounts.permissions import IsAdminOrReadOnlyRole
from devices.authentication import DeviceAPIKeyAuthentication
from devices.permissions import IsDeviceRequest

from alerts.models import Alert
from persons.models import PersonOfInterest
from persons.services import compare_encoding, get_face_encoding

from .models import DetectionEvent, FacialMatchResult
from .serializers import DetectionEventSerializer


logger = logging.getLogger(__name__)


class CameraRecognitionView(APIView):
    """Accept one ESP32-CAM JPEG and return its face-match result synchronously."""

    authentication_classes = [DeviceAPIKeyAuthentication]
    permission_classes = [IsDeviceRequest]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # ``image`` is the supported firmware field. ``imageFile`` is accepted
        # temporarily so deployed devices using the old snapshot endpoint can be
        # migrated without a flag day.
        image_file = request.FILES.get("image") or request.FILES.get("imageFile")
        if image_file is None:
            return Response(
                {"status": "failed", "error": "Multipart field 'image' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if image_file.content_type and not image_file.content_type.startswith("image/"):
            return Response(
                {"status": "failed", "error": "The image field must contain an image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = request.auth.device
        camera_id = request.headers.get("X-Camera-ID") or request.data.get("device_id")
        if camera_id and camera_id != device.device_id:
            return Response(
                {"status": "failed", "error": "Camera ID does not match the device API key."},
                status=status.HTTP_403_FORBIDDEN,
            )

        trigger_source = request.data.get("trigger_source", DetectionEvent.TriggerSource.MOTION)
        if trigger_source not in DetectionEvent.TriggerSource.values:
            return Response(
                {"status": "failed", "error": "Invalid trigger_source."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Saving first gives the event an audit trail even when no face is found.
        detection = DetectionEvent.objects.create(
            device=device,
            zone=device.zone,
            image=image_file,
            trigger_source=trigger_source,
        )
        result = FacialMatchResult.objects.create(detection=detection)

        try:
            encoding = get_face_encoding(detection.image)
            if encoding is None:
                result.status = FacialMatchResult.Status.UNMATCHED
                result.error_message = "No face detected in image."
                result.save(update_fields=["status", "error_message", "updated_at"])
                detection.processing_status = DetectionEvent.ProcessingStatus.PROCESSED
                detection.save(update_fields=["processing_status"])
                return self._response(detection, result, status.HTTP_201_CREATED)

            person, confidence, distance = compare_encoding(
                encoding,
                PersonOfInterest.objects.exclude(face_encoding__isnull=True),
                settings.FACE_MATCH_TOLERANCE,
            )

            with transaction.atomic():
                result.person = person
                result.confidence_score = confidence
                result.face_distance = distance
                result.status = (
                    FacialMatchResult.Status.MATCHED if person else FacialMatchResult.Status.UNMATCHED
                )
                result.error_message = "" if distance is not None else "No enrolled face encodings are available."
                result.save()

                detection.processing_status = DetectionEvent.ProcessingStatus.PROCESSED
                detection.save(update_fields=["processing_status"])

                if person:
                    Alert.objects.create(
                        detection=detection,
                        match_result=result,
                        person=person,
                        source=Alert.Source.FACIAL_MATCH,
                        severity={
                            "low": Alert.Severity.LOW,
                            "medium": Alert.Severity.HIGH,
                            "high": Alert.Severity.CRITICAL,
                        }.get(person.threat_level, Alert.Severity.MEDIUM),
                        message=f"Facial match detected for {person.full_name}.",
                    )
            return self._response(detection, result, status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Facial recognition failed for camera detection %s", detection.id)
            result.status = FacialMatchResult.Status.FAILED
            result.error_message = "Facial recognition processing failed."
            result.save(update_fields=["status", "error_message", "updated_at"])
            detection.processing_status = DetectionEvent.ProcessingStatus.FAILED
            detection.save(update_fields=["processing_status"])
            return self._response(detection, result, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def _response(detection, result, response_status):
        person = result.person
        return Response(
            {
                "status": result.status,
                "matched": result.status == FacialMatchResult.Status.MATCHED,
                "detection_id": detection.id,
                "camera_id": detection.device.device_id,
                "subject": (
                    {
                        "id": person.id,
                        "name": person.full_name,
                        "threat_level": person.threat_level,
                    }
                    if person
                    else None
                ),
                "confidence": result.confidence_score,
                "face_distance": result.face_distance,
                "error": result.error_message or None,
            },
            status=response_status,
        )

# Optional real-time updates (Uncomment if using Django Channels)
# from asgiref.sync import async_to_sync
# from channels.layers import get_channel_layer


class DetectionEventViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DetectionEventSerializer
    throttle_scope = "detection_ingest"

    def get_queryset(self):
        # Keeps database roundtrips fully optimized
        return DetectionEvent.objects.select_related("device", "match_result").all()

    def get_authenticators(self):
        if self.action == "create":
            return [DeviceAPIKeyAuthentication()]
        return super().get_authenticators()

    def get_permissions(self):
        if self.action == "create":
            return [IsDeviceRequest()]
        return [IsAdminOrReadOnlyRole()]

    def create(self, request, *args, **kwargs):
        """
        Unified ingestion engine that handles incoming traffic from both hardwares:
        1. Main ESP32 Node (JSON Telemetry logs)
        2. ESP32-CAM (Multipart Image Data + Face Recognition confirmation flags)
        """
        # Determine the source device profile checking the request format structure
        device_id = request.data.get("device_id") or request.POST.get("device_id", "UNKNOWN_NODE")
        
        # --- PATHWAY A: ESP32-CAM MULTIPART SNAPSHOT PROCESSING ---
        if "imageFile" in request.FILES:
            image_file = request.FILES["imageFile"]
            
            # Extract face detection boolean parameter from the multipart payload
            face_detected = request.POST.get("face_detected", "false").lower() == "true"
            
            # Generate a unique timestamped file path structure
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "FACE_MATCH_" if face_detected else "SNAP_"
            filename = f"security_snapshots/{prefix}{device_id}_{timestamp}.jpg"
            
            # Commit raw image file data directly to server media disk
            saved_path = default_storage.save(filename, ContentFile(image_file.read()))
            absolute_media_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)
            
            # Build camera notification dictionary profile
            event_tag = "FACE_VERIFIED_LOCK" if face_detected else "CAMERA_SNAP_CAPTURE"
            status_msg = f"Snapshot saved at: {saved_path}"
            
            # 📝 If you want to log this directly to your database through the serializer:
            # mutation_data = {
            #     "device": request.user.device.id, # Mapping out tracking targets
            #     "event_type": event_tag,
            #     "notes": f"Image URL: {absolute_media_url}"
            # }
            # serializer = self.get_serializer(data=mutation_data)
            # serializer.is_valid(raise_exception=True)
            # self.perform_create(serializer)
            
            print(f"📸 [ESP32-CAM Alert] Face Locked: {face_detected} | URL: {absolute_media_url}")
            
            # Real-Time Broadcast Hook Engine
            self._broadcast_to_frontend({
                "device_id": device_id,
                "event_type": event_tag,
                "face_detected": face_detected,
                "image_url": absolute_media_url,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            return Response({
                "status": "processed",
                "face_detected": face_detected,
                "image_url": absolute_media_url
            }, status=status.HTTP_201_CREATED)
            
        # --- PATHWAY B: MAIN ESP32 TELEMETRY PROCESSING ---
        else:
            event_type = request.data.get("event_type", "SECURE_HEARTBEAT")
            status_msg = request.data.get("status", "")
            
            print(f"📡 [Main Node Ingest] {event_type} | {status_msg}")
            
            # Route payload data using standard DRF serializer serialization
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            
            # Append exact live timestamp details to push metrics smoothly to web client interface
            broadcast_data = dict(serializer.data)
            broadcast_data["timestamp"] = datetime.datetime.now().isoformat()
            
            self._broadcast_to_frontend(broadcast_data)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def _broadcast_to_frontend(self, payload):
        """
        Helper channel execution routing module to immediately mirror background log events
        directly to your React frontend application dashboard views.
        """
        # try:
        #     channel_layer = get_channel_layer()
        #     async_to_sync(channel_layer.group_send)(
        #         "security_alerts",
        #         {
        #             "type": "security_broadcast",
        #             "message": payload
        #         }
        #     )
        # except Exception as e:
        #     print(f"WebSocket Broadcast omitted: {str(e)}")
        pass
