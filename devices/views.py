from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrReadOnlyRole
from .authentication import DeviceAPIKeyAuthentication
from .permissions import IsDeviceRequest
from .serializers import DeviceHeartbeatSerializer, DeviceSerializer
from alerts.broadcast import broadcast_alert_event


class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAdminOrReadOnlyRole]

    def get_queryset(self):
        from .models import Device
        return Device.objects.all()


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
        device = serializer.save()
        payload = DeviceSerializer(device).data
        broadcast_alert_event("device.heartbeat", payload)
        return Response(payload, status=status.HTTP_200_OK)