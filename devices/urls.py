from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DeviceHeartbeatView, DeviceViewSet

router = DefaultRouter()
router.register("devices", DeviceViewSet, basename="device")

urlpatterns = [
    path("devices/heartbeat/", DeviceHeartbeatView.as_view(), name="device-heartbeat"),
    *router.urls,
]
