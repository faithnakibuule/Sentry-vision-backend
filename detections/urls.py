from rest_framework.routers import DefaultRouter

from .views import DetectionEventViewSet

router = DefaultRouter()
router.register("detections", DetectionEventViewSet, basename="detection")

urlpatterns = router.urls
