from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from sentry_vision.views import AuthenticatedMediaView


def home(request):
    return JsonResponse({
        "status": "ok",
        "service": "Sentry Vision backend",
        "api_root": "/api/",
    })

urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
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
