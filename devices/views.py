import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response

# Preserving your exact architectural imports
from accounts.permissions import IsAdminOrReadOnlyRole
from devices.authentication import DeviceAPIKeyAuthentication
from devices.permissions import IsDeviceRequest

from .models import DetectionEvent, FacialMatchResult
from .serializers import DetectionEventSerializer
from .tasks import process_detection_event

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
        # --- PATHWAY A: ESP32-CAM MULTIPART SNAPSHOT PROCESSING ---
        if "imageFile" in request.FILES:
            return self._handle_camera_snapshot(request)

        # --- PATHWAY B: MAIN ESP32 TELEMETRY PROCESSING ---
        return self._handle_telemetry(request)

    def _handle_camera_snapshot(self, request):
        """
        Creates a real DetectionEvent (through the same model your serializer
        uses) so the capture actually enters the facial-recognition pipeline,
        instead of just being written to local disk and logged to console.
        """
        device = request.auth.device

        image_file = request.FILES["imageFile"]
        trigger_source = request.POST.get("trigger_source", DetectionEvent.TriggerSource.MANUAL)
        servo_angle = request.POST.get("servo_angle") or None
        distance_cm = request.POST.get("distance_cm") or None

        detection = DetectionEvent.objects.create(
            device=device,
            image=ContentFile(image_file.read(), name=image_file.name),
            trigger_source=trigger_source,
            servo_angle=servo_angle,
            distance_cm=distance_cm,
            zone=device.zone,
            timestamp=timezone.now(),
            processing_status=DetectionEvent.ProcessingStatus.PENDING,
        )
        FacialMatchResult.objects.get_or_create(detection=detection)
        device.mark_seen()

        # Queue the exact same background task your telemetry/serializer
        # pathway already uses, so encoding + comparison + alerting is
        # handled in one consistent place instead of being duplicated here.
        transaction.on_commit(lambda: process_detection_event.delay(detection.id))

        payload = {
            "device_id": device.device_id,
            "detection_id": detection.id,
            "processing_status": detection.processing_status,
            "image_url": request.build_absolute_uri(detection.image.url) if detection.image else None,
            "timestamp": detection.timestamp.isoformat(),
        }

        self._broadcast_to_frontend(payload)

        return Response(payload, status=status.HTTP_201_CREATED)

    def _handle_telemetry(self, request):
        event_type = request.data.get("event_type", "SECURE_HEARTBEAT")
        status_msg = request.data.get("status", "")

        print(f"📡 [Main Node Ingest] {event_type} | {status_msg}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

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