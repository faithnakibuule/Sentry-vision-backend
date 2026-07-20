from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenRefreshView

def health_check(request):
    return JsonResponse({"status": "ok"})

from sentry_vision.views import AuthenticatedMediaView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check),
    path("api/", include("accounts.urls")),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/media/<path:path>", AuthenticatedMediaView.as_view(), name="protected-media"),
    path("api/", include("devices.urls")),
    path("api/", include("persons.urls")),
    path("api/", include("detections.urls")),
    path("api/", include("alerts.urls")),
    path("api/", include("radar.urls")),
    path("api/", include("analytics.urls")),
    path("api/", include("logs.urls")),
]
