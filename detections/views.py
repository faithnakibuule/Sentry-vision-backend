from rest_framework import mixins, viewsets

from accounts.permissions import IsAdminOrReadOnlyRole
from devices.authentication import DeviceAPIKeyAuthentication
from devices.permissions import IsDeviceRequest

from .models import DetectionEvent
from .serializers import DetectionEventSerializer


class DetectionEventViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DetectionEventSerializer
    throttle_scope = "detection_ingest"

    def get_queryset(self):
        return DetectionEvent.objects.select_related("device", "match_result").all()

    def get_authenticators(self):
        if self.action == "create":
            return [DeviceAPIKeyAuthentication()]
        return super().get_authenticators()

    def get_permissions(self):
        if self.action == "create":
            return [IsDeviceRequest()]
        return [IsAdminOrReadOnlyRole()]
