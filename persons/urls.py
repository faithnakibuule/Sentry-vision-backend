from rest_framework.routers import DefaultRouter

from .views import PersonOfInterestViewSet

router = DefaultRouter()
router.register("persons", PersonOfInterestViewSet, basename="person")

urlpatterns = router.urls
