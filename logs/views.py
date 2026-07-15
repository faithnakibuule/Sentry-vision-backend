from rest_framework import mixins, viewsets

from accounts.permissions import IsAdminRole
from devices.authentication import DeviceAPIKeyAuthentication
from devices.permissions import IsDeviceRequest

from .models import SystemLog
from .serializers import SystemLogSerializer


class SystemLogViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = SystemLogSerializer

    def get_queryset(self):
        return SystemLog.objects.select_related("device").all()

    def get_authenticators(self):
        if self.action == "create":
            return [DeviceAPIKeyAuthentication()]
        return super().get_authenticators()

    def get_permissions(self):
        if self.action == "create":
            return [IsDeviceRequest()]
        return [IsAdminRole()]
