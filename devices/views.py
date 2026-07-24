from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

<<<<<<< HEAD
from accounts.permissions import IsAdminOrReadOnlyRole, IsAdminRole
from alerts.broadcast import broadcast_alert_event

from .authentication import DeviceAPIKeyAuthentication
from .models import Device, DeviceAPIKey, DeviceStatus
=======
from accounts.permissions import IsAdminOrReadOnlyRole
from .authentication import DeviceAPIKeyAuthentication
>>>>>>> 20d2b0cc7b4871c9d2fb33d035a68337f0305177
from .permissions import IsDeviceRequest
from .serializers import (
    DeviceHeartbeatSerializer,
    DeviceSerializer,
    DeviceStatusSerializer,
)


class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAdminOrReadOnlyRole]

    def get_queryset(self):
<<<<<<< HEAD
        return Device.objects.all()


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
            return Response(
                {"error": "device_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Device.objects.filter(device_id=device_id).exists():
            return Response(
                {
                    "error": f"Device '{device_id}' already exists. Use a different device_id."
                },
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


=======
        from .models import Device
        return Device.objects.all()


>>>>>>> 20d2b0cc7b4871c9d2fb33d035a68337f0305177
class DeviceHeartbeatView(APIView):
    """Authenticated heartbeat endpoint for primary registered devices."""

    authentication_classes = [DeviceAPIKeyAuthentication]
    permission_classes = [IsDeviceRequest]

    def post(self, request):
        serializer = DeviceHeartbeatSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        device = serializer.save()
        payload = DeviceSerializer(device).data
        broadcast_alert_event("device.heartbeat", payload)
        return Response(payload, status=status.HTTP_200_OK)
<<<<<<< HEAD


class DeviceStatusHeartbeatView(APIView):
    """ESP32 POSTs here on every sub-device / sensor read cycle."""

    authentication_classes = [DeviceAPIKeyAuthentication]
    permission_classes = [IsDeviceRequest]

    def post(self, request):
        device = request.auth.device  # ⚠️ confirm this attribute — see note below
        sensor_type = request.data.get("device_id")  # e.g. "ultrasonic", "servo_1"
        payload = request.data.get("payload", {})

        valid_choices = dict(DeviceStatus.SensorType.choices)
        if sensor_type not in valid_choices:
            return Response(
                {"error": f"unknown sensor_type '{sensor_type}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj, _ = DeviceStatus.objects.update_or_create(
            device=device,
            sensor_type=sensor_type,
            defaults={"payload": payload},
        )
        return Response(DeviceStatusSerializer(obj).data, status=status.HTTP_200_OK)
    
class DeviceHealthListView(APIView):
    """Frontend polls here to render the device health panel."""

    permission_classes = [IsAdminOrReadOnlyRole]

    def get(self, request):
        qs = DeviceStatus.objects.all()
        data = DeviceStatusSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)
=======
        device = serializer.save()
        payload = DeviceSerializer(device).data
        broadcast_alert_event("device.heartbeat", payload)
        return Response(payload, status=status.HTTP_200_OK)
>>>>>>> 20d2b0cc7b4871c9d2fb33d035a68337f0305177
