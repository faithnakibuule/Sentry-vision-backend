from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DeviceHealthListView,
    DeviceHeartbeatView,
    DeviceProvisionView,
    DeviceStatusHeartbeatView,
    DeviceViewSet,
)

router = DefaultRouter()
router.register("devices", DeviceViewSet, basename="device")

urlpatterns = [
    # Registered devices endpoints
    path("devices/heartbeat/", DeviceHeartbeatView.as_view(), name="device-heartbeat"),
    path("devices/provision/", DeviceProvisionView.as_view(), name="device-provision"),
    
    # Sub-device / Sensor status endpoints
    path("devices/status-heartbeat/", DeviceStatusHeartbeatView.as_view(), name="device-status-heartbeat"),
    path("devices/health/", DeviceHealthListView.as_view(), name="device-health"),
    
    # Router endpoints (CRUD /api/devices/)
    *router.urls,
]