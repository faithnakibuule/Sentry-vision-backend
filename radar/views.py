from rest_framework import mixins, viewsets

from accounts.permissions import IsAdminOrReadOnlyRole
from devices.authentication import DeviceAPIKeyAuthentication
from devices.permissions import IsDeviceRequest

from .models import RadarReading
from .serializers import RadarReadingSerializer


class RadarReadingViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RadarReadingSerializer

    def get_queryset(self):
        return RadarReading.objects.select_related("device").all()

    def get_authenticators(self):
        if self.action == "create":
            return [DeviceAPIKeyAuthentication()]
        return super().get_authenticators()

    def get_permissions(self):
        if self.action == "create":
            return [IsDeviceRequest()]
        return [IsAdminOrReadOnlyRole()]
