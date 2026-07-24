import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response

from accounts.permissions import IsAdminOrReadOnlyRole, IsAdminRole

from .authentication import DeviceAPIKeyAuthentication
from .models import Device, DeviceAPIKey
from .permissions import IsDeviceRequest
from .serializers import DeviceHeartbeatSerializer, DeviceSerializer
from alerts.broadcast import broadcast_alert_event


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

class DeviceProvisionView(APIView):
    """
    Admin-only endpoint that creates a Device and issues its API key in one
    call, returning the raw key. This exists so devices can be provisioned
    without needing shell/console access to the backend (e.g. on Render's
    free tier, which has no Shell tab).

    POST /api/devices/provision/
    {
        "device_id": "esp32-sentry-node-01",
        "device_type": "arduino_uno",
        "zone": "front-yard",
        "label": "Sentry Main Node"
    }

    Response includes "raw_key" — copy it immediately, it is only ever
    shown this once. Requires a logged-in admin (Authorization: Bearer <access token>).
    """

    permission_classes = [IsAdminRole]

    def post(self, request):
        device_id = request.data.get("device_id")
        if not device_id:
            return Response({"error": "device_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if Device.objects.filter(device_id=device_id).exists():
            return Response(
                {"error": f"Device '{device_id}' already exists. Use a different device_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = Device.objects.create(
            device_id=device_id,
            device_type=request.data.get("device_type", "arduino_uno"),
            zone=request.data.get("zone", "default"),
            label=request.data.get("label", ""),
        )
        api_key, raw_key = DeviceAPIKey.issue_key(device)

        return Response(
            {
                "device": DeviceSerializer(device).data,
                "raw_key": raw_key,
                "warning": "Copy raw_key now — it will not be shown again.",
            },
            status=status.HTTP_201_CREATED,
        )


class DeviceHeartbeatView(APIView):
    authentication_classes = [DeviceAPIKeyAuthentication]
    permission_classes = [IsDeviceRequest]

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
        device = serializer.save()
        payload = DeviceSerializer(device).data
        broadcast_alert_event("device.heartbeat", payload)
        return Response(payload, status=status.HTTP_200_OK)
