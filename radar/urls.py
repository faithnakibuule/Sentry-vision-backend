from rest_framework.routers import DefaultRouter

from .views import RadarReadingViewSet

router = DefaultRouter()
router.register("radar-readings", RadarReadingViewSet, basename="radar-reading")

urlpatterns = router.urls
