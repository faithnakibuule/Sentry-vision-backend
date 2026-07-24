from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DeviceHeartbeatView, DeviceProvisionView, DeviceViewSet, telemetry_view

router = DefaultRouter()
router.register("devices", DeviceViewSet, basename="device")

urlpatterns = [
    path("devices/heartbeat/", DeviceHeartbeatView.as_view(), name="device-heartbeat"),
    path("devices/provision/", DeviceProvisionView.as_view(), name="device-provision"),
    
    # Clean route (Main project urls.py provides the leading "api/")
    path("telemetry/", telemetry_view, name="telemetry"),
    
    *router.urls,
]