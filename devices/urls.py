from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DeviceHeartbeatView, DeviceProvisionView, DeviceViewSet, telemetry_view

router = DefaultRouter()
router.register("devices", DeviceViewSet, basename="device")

urlpatterns = [
    path("devices/heartbeat/", DeviceHeartbeatView.as_view(), name="device-heartbeat"),
    path("devices/provision/", DeviceProvisionView.as_view(), name="device-provision"),
    
    # Changed from 'api/telemetry/' to 'telemetry/'
    path("telemetry/", telemetry_view, name="telemetry"), 
    
    *router.urls,
]