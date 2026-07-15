from rest_framework.permissions import BasePermission

from .models import DeviceAPIKey


class IsDeviceRequest(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, DeviceAPIKey)
