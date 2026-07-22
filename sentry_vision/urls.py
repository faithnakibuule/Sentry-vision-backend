from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.conf import settings
from rest_framework_simplejwt.views import TokenRefreshView
from sentry_vision.views import AuthenticatedMediaView
from django.conf.urls.static import static
from api import views

def health_check(request):
    return JsonResponse({"status": "ok"})

def home(request):
    return JsonResponse({
        "status": "ok",
        "service": "Sentry Vision backend",
        "api_root": "/api/",
    })

urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("health/", health_check),

    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/media/<path:path>", AuthenticatedMediaView.as_view(), name="protected-media"),

    path("api/", include("accounts.urls")),
    path("api/", include("devices.urls")),
    path("api/", include("persons.urls")),
    path("api/", include("detections.urls")),
    path("api/", include("alerts.urls")),
    path("api/", include("radar.urls")),
    path("api/", include("analytics.urls")),
    path("api/", include("logs.urls")),
    path('upload_live', views.upload_live, name='upload_live_direct'),
    path('upload_live/', views.upload_live, name='upload_live_direct_slash'),
    path('api/', include('api.urls')),
]
# Serve media files (uploaded JPEG snapshots) during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)