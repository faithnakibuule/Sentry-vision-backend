from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrReadOnlyRole, IsAdminRole

from .authentication import DeviceAPIKeyAuthentication
from .models import Device, DeviceAPIKey
from .permissions import IsDeviceRequest
from .serializers import DeviceHeartbeatSerializer, DeviceSerializer
from alerts.broadcast import broadcast_alert_event


class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAdminOrReadOnlyRole]

    def get_queryset(self):
        from .models import Device

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

    def post(self, request):
        serializer = DeviceHeartbeatSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        device = serializer.save()
        payload = DeviceSerializer(device).data
        broadcast_alert_event("device.heartbeat", payload)
        return Response(payload, status=status.HTTP_200_OK)