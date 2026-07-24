from django.urls import path
from rest_framework.routers import DefaultRouter

<<<<<<< HEAD
from .views import (
    DeviceHealthListView,
    DeviceHeartbeatView,
    DeviceProvisionView,
    DeviceStatusHeartbeatView,
    DeviceViewSet,
)
=======
from .views import DeviceHeartbeatView, DeviceProvisionView, DeviceViewSet, telemetry_view
>>>>>>> 20d2b0cc7b4871c9d2fb33d035a68337f0305177

router = DefaultRouter()
router.register("devices", DeviceViewSet, basename="device")

urlpatterns = [
    # Registered devices endpoints
    path("devices/heartbeat/", DeviceHeartbeatView.as_view(), name="device-heartbeat"),
    path("devices/provision/", DeviceProvisionView.as_view(), name="device-provision"),
    
<<<<<<< HEAD
    # Sub-device / Sensor status endpoints
    path("devices/status-heartbeat/", DeviceStatusHeartbeatView.as_view(), name="device-status-heartbeat"),
    path("devices/health/", DeviceHealthListView.as_view(), name="device-health"),
    
    # Router endpoints (CRUD /api/devices/)
=======
    # Clean route (Main project urls.py provides the leading "api/")
    path("telemetry/", telemetry_view, name="telemetry"),
    
>>>>>>> 20d2b0cc7b4871c9d2fb33d035a68337f0305177
    *router.urls,
]