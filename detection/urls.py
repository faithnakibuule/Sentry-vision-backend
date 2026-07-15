from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsSummaryView,
    CurrentUserView,
    DashboardFeedView,
    DetectionStatusUpdateView,
    DetectionUploadView,
    DeviceHeartbeatView,
    DeviceListView,
    LiveDashboardSummaryView,
    LoginView,
    RadarTelemetryUploadView,
    SuspectProfileViewSet,
    SystemSettingsView,
)

# ModelViewSet -> router gives us GET/POST /api/suspects/ and
# GET/PUT/PATCH/DELETE /api/suspects/<id>/ from one class (see views.py).
router = DefaultRouter()
router.register("suspects", SuspectProfileViewSet, basename="suspect")

urlpatterns = [
    # --- Device-facing (ESP32-CAM / Arduino / RUView radar) ---
    path("detections/upload/", DetectionUploadView.as_view(), name="detection-upload"),
    path("telemetry/ruview/", RadarTelemetryUploadView.as_view(), name="ruview-telemetry"),
    path("devices/heartbeat/", DeviceHeartbeatView.as_view(), name="device-heartbeat"),

    # --- Dashboard-facing (Admin / Security Viewer) ---
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/me/", CurrentUserView.as_view(), name="auth-me"),

    path("dashboard/", DashboardFeedView.as_view(), name="dashboard-feed"),
    path("dashboard/summary/", LiveDashboardSummaryView.as_view(), name="dashboard-summary"),
    path(
        "detections/<int:pk>/status/",
        DetectionStatusUpdateView.as_view(),
        name="detection-status-update",
    ),

    path("devices/", DeviceListView.as_view(), name="device-list"),
    path("settings/", SystemSettingsView.as_view(), name="system-settings"),
    path("analytics/summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),

    path("", include(router.urls)),  # /api/suspects/, /api/suspects/<id>/
]