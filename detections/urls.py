from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import CameraRecognitionView, DetectionEventViewSet

router = DefaultRouter()
router.register("detections", DetectionEventViewSet, basename="detection")

urlpatterns = [
    path("detections/recognize/", CameraRecognitionView.as_view(), name="camera-recognize"),
    *router.urls,
]
