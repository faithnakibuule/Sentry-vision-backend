from rest_framework.routers import DefaultRouter

from .views import SystemLogViewSet

router = DefaultRouter()
router.register("logs", SystemLogViewSet, basename="log")

urlpatterns = router.urls
