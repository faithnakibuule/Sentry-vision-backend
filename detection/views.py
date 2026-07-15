import logging

from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .consumers import broadcast_live_event
from .face_utils import match_detection_image
from .models import DetectionLog, DeviceNode, RadarTelemetry, SuspectProfile, SystemSettings
from .permissions import IsAdmin, IsAdminOrReadOnly, IsAuthenticatedRole
from .serializers import (
    DetectionLogSerializer,
    DetectionStatusUpdateSerializer,
    DetectionUploadSerializer,
    DeviceHeartbeatSerializer,
    DeviceNodeSerializer,
    LoginSerializer,
    RadarTelemetrySerializer,
    RadarTelemetryUploadSerializer,
    SuspectProfileCreateSerializer,
    SuspectProfileSerializer,
    SystemSettingsSerializer,
    UserProfileSerializer,
)

logger = logging.getLogger("sentry_vision.views")

# How recent a DetectionLog has to be to be considered "active" for the
# purpose of auto-linking an incoming RUView radar reading to it.
RADAR_LINK_WINDOW_SECONDS = 30


class DetectionUploadView(APIView):
    """
    POST /api/detections/upload/

    Consumes a multipart/form-data burst-capture image from the ESP32-CAM,
    runs it through the facial recognition engine, persists a DetectionLog
    entry either way, and returns a compact JSON payload the edge node can
    render straight onto its OLED.

    Device-facing: no user login, so permission is explicitly AllowAny
    even though the project default is now token auth (see settings.py).
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]
    authentication_classes = []  # skip token auth entirely for this device endpoint

    def post(self, request, *args, **kwargs):
        upload_serializer = DetectionUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)

        # Save first so we have a persisted image file to re-read for
        # encoding, and a DetectionLog row to attach the match result to.
        detection = upload_serializer.save()

        suspects = SuspectProfile.objects.exclude(face_encoding__isnull=True)
        match_result = match_detection_image(detection.captured_photo, suspects)

        matched_suspect = match_result["matched_suspect"]
        confidence = match_result["confidence"]

        detection.is_matched = matched_suspect is not None
        detection.match_confidence = confidence
        detection.matched_suspect = matched_suspect
        # status stays PENDING here — that's the whole point of the Alerts
        # workflow: a human confirms/dismisses it next, even on a match.
        detection.save(update_fields=["is_matched", "match_confidence", "matched_suspect"])

        if matched_suspect is not None:
            message = f"MATCH: {matched_suspect.name}"
            suspect_payload = SuspectProfileSerializer(
                matched_suspect, context={"request": request}
            ).data
        elif match_result["face_found"]:
            message = "No match found in suspect database."
            suspect_payload = None
        else:
            message = "No face detected in captured image."
            suspect_payload = None

        response_payload = {
            "detection_id": detection.id,
            "is_matched": detection.is_matched,
            "match_confidence": detection.match_confidence,
            "suspect": suspect_payload,
            "message": message,
        }

        # Push to every connected dashboard over ws/live/ so the Live
        # Dashboard feed and Alerts table update instantly, no polling.
        broadcast_live_event(
            "new_detection",
            DetectionLogSerializer(detection, context={"request": request}).data,
        )

        return Response(response_payload, status=status.HTTP_201_CREATED)


class RadarTelemetryUploadView(APIView):
    """
    POST /api/telemetry/ruview/

    Accepts a JSON payload from the RUView Wi-Fi through-wall radar
    subsystem and stores it, auto-linking it to the most recent
    DetectionLog (within RADAR_LINK_WINDOW_SECONDS) if one exists so the
    dashboard can correlate "who" with "how they're behaving".
    """

    parser_classes = [JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RadarTelemetryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reading = serializer.save()

        latest_detection = (
            DetectionLog.objects.order_by("-timestamp").first()
        )
        if latest_detection is not None:
            age_seconds = (timezone.now() - latest_detection.timestamp).total_seconds()
            if age_seconds <= RADAR_LINK_WINDOW_SECONDS:
                reading.associated_detection = latest_detection
                reading.save(update_fields=["associated_detection"])

        # Powers the Radar View's live presence/heart-rate/movement overlay.
        broadcast_live_event("radar_update", RadarTelemetrySerializer(reading).data)

        return Response(
            RadarTelemetrySerializer(reading).data, status=status.HTTP_201_CREATED
        )


class DashboardFeedView(APIView):
    """
    GET /api/dashboard/

    Returns the unified "culprit list": every DetectionLog, newest first,
    with the matched suspect's details (if any) and any RUView telemetry
    correlated with it. Powers the Alerts/Incidents table (it supports
    client-side filtering via ?status=PENDING etc. since the dataset is
    small; move filtering server-side if the log grows large).
    """

    permission_classes = [IsAuthenticatedRole]

    def get(self, request, *args, **kwargs):
        detections = (
            DetectionLog.objects.select_related("matched_suspect")
            .prefetch_related("radar_readings")
            .all()
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            detections = detections.filter(status=status_filter.upper())

        serializer = DetectionLogSerializer(
            detections, many=True, context={"request": request}
        )
        return Response(
            {
                "count": detections.count(),
                "results": serializer.data,
            }
        )


class LiveDashboardSummaryView(APIView):
    """
    GET /api/dashboard/summary/

    Purpose-built for the "Live Dashboard" page's status strip: device
    online/offline counts, active (PENDING) alert count, the last 5
    detections, and a mini radar presence indicator (most recent reading
    per zone). This is intentionally a *separate*, cheaper endpoint from
    the full culprit list in DashboardFeedView so the page that's open
    all day doesn't have to paginate through the entire history.
    """

    permission_classes = [IsAuthenticatedRole]

    def get(self, request, *args, **kwargs):
        settings_row = SystemSettings.load()
        threshold = settings_row.device_offline_threshold_seconds

        devices = list(DeviceNode.objects.all())
        online_count = sum(1 for d in devices if d.is_online(threshold))

        active_alert_count = DetectionLog.objects.filter(
            status=DetectionLog.STATUS_PENDING
        ).count()

        last_five = (
            DetectionLog.objects.select_related("matched_suspect")
            .order_by("-timestamp")[:5]
        )

        # "Mini radar presence indicator": latest reading per zone, most
        # recent zones first. Small in-memory dedupe since the RUView
        # subsystem is a handful of zones, not thousands.
        latest_per_zone = {}
        for reading in RadarTelemetry.objects.order_by("-timestamp")[:100]:
            if reading.zone and reading.zone not in latest_per_zone:
                latest_per_zone[reading.zone] = reading

        return Response(
            {
                "devices_online": online_count,
                "devices_total": len(devices),
                "active_alert_count": active_alert_count,
                "recent_detections": DetectionLogSerializer(
                    last_five, many=True, context={"request": request}
                ).data,
                "radar_presence": RadarTelemetrySerializer(
                    list(latest_per_zone.values()), many=True
                ).data,
            }
        )


class DetectionStatusUpdateView(APIView):
    """
    PATCH /api/detections/<id>/status/
    Body: {"status": "CONFIRMED"}  or  {"status": "DISMISSED"}

    The "acknowledge alert" action. Available to BOTH Admin and Security
    Viewer roles (IsAuthenticatedRole, not IsAdmin) — this is the one
    write action a read-only Viewer is explicitly allowed to perform,
    per the frontend spec ("read + acknowledge alerts only").
    """

    permission_classes = [IsAuthenticatedRole]

    def patch(self, request, pk, *args, **kwargs):
        try:
            detection = DetectionLog.objects.get(pk=pk)
        except DetectionLog.DoesNotExist:
            return Response({"detail": "Detection not found."}, status=404)

        serializer = DetectionStatusUpdateSerializer(
            detection, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        payload = DetectionLogSerializer(detection, context={"request": request}).data
        broadcast_live_event("detection_status", payload)
        return Response(payload)


class SuspectProfileViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for the Persons of Interest gallery:
      GET    /api/suspects/          list (Admin + Viewer)
      POST   /api/suspects/          create (Admin only)
      GET    /api/suspects/<id>/     retrieve (Admin + Viewer)
      PUT/PATCH /api/suspects/<id>/  update (Admin only)
      DELETE /api/suspects/<id>/     delete (Admin only)

    IsAdminOrReadOnly enforces the split; ModelViewSet + a DRF router
    (see urls.py) generates all five routes from this one class.
    """

    queryset = SuspectProfile.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SuspectProfileCreateSerializer
        return SuspectProfileSerializer


class DeviceHeartbeatView(APIView):
    """
    POST /api/devices/heartbeat/

    Called periodically by every ESP32-CAM / Arduino Uno / RUView radar
    node. Auto-registers the device on first contact (get_or_create on
    device_id) and refreshes its health fields + last_heartbeat.
    Device-facing: AllowAny, same reasoning as the upload/telemetry views.
    """

    parser_classes = [JSONParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        device_id = request.data.get("device_id")
        if not device_id:
            return Response({"detail": "device_id is required."}, status=400)

        device, _created = DeviceNode.objects.get_or_create(device_id=device_id)

        serializer = DeviceHeartbeatSerializer(device, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        device = serializer.save(last_heartbeat=timezone.now())

        settings_row = SystemSettings.load()
        payload = DeviceNodeSerializer(
            device,
            context={"offline_threshold_seconds": settings_row.device_offline_threshold_seconds},
        ).data
        broadcast_live_event("device_status", payload)

        return Response(payload, status=status.HTTP_200_OK)


class DeviceListView(APIView):
    """
    GET /api/devices/

    Powers the Device Health page: every known device with its computed
    online/offline status, last heartbeat, SD card usage, and power status.
    """

    permission_classes = [IsAuthenticatedRole]

    def get(self, request, *args, **kwargs):
        settings_row = SystemSettings.load()
        devices = DeviceNode.objects.all()
        serializer = DeviceNodeSerializer(
            devices,
            many=True,
            context={"offline_threshold_seconds": settings_row.device_offline_threshold_seconds},
        )
        return Response(serializer.data)


class SystemSettingsView(APIView):
    """
    GET /api/settings/   — any logged-in user can view current settings
    PUT /api/settings/   — Admin only, updates the singleton settings row

    Backs the Settings page: detection thresholds, alert channels. User
    role management is handled separately via Django admin / the
    UserProfile model rather than this endpoint.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticatedRole()]
        return [IsAdmin()]

    def get(self, request, *args, **kwargs):
        return Response(SystemSettingsSerializer(SystemSettings.load()).data)

    def put(self, request, *args, **kwargs):
        instance = SystemSettings.load()
        serializer = SystemSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AnalyticsSummaryView(APIView):
    """
    GET /api/analytics/summary/?days=7

    Aggregates DetectionLog history for the Analytics page: detections
    per day, false-positive rate (DISMISSED / total confirmed-or-dismissed),
    and the busiest zones/hours. Polling-friendly (no WebSocket needed) —
    the frontend spec explicitly allows polling here.
    """

    permission_classes = [IsAuthenticatedRole]

    def get(self, request, *args, **kwargs):
        days = int(request.query_params.get("days", 7))
        since = timezone.now() - timezone.timedelta(days=days)
        qs = DetectionLog.objects.filter(timestamp__gte=since)

        # Detections per day (SQLite-safe date truncation via python side,
        # since TruncDate needs backend-specific handling we want to keep
        # this DB-agnostic for the dev SQLite setup).
        per_day = {}
        for det in qs.only("timestamp"):
            day_key = det.timestamp.date().isoformat()
            per_day[day_key] = per_day.get(day_key, 0) + 1

        total_triaged = qs.filter(
            status__in=[DetectionLog.STATUS_CONFIRMED, DetectionLog.STATUS_DISMISSED]
        ).count()
        dismissed = qs.filter(status=DetectionLog.STATUS_DISMISSED).count()
        false_positive_rate = round(dismissed / total_triaged, 4) if total_triaged else None

        busiest_zones = (
            qs.exclude(zone="")
            .values("zone")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        busiest_hours = {}
        for det in qs.only("timestamp"):
            hour_key = det.timestamp.hour
            busiest_hours[hour_key] = busiest_hours.get(hour_key, 0) + 1
        busiest_hours_sorted = sorted(
            busiest_hours.items(), key=lambda kv: kv[1], reverse=True
        )[:5]

        return Response(
            {
                "range_days": days,
                "total_detections": qs.count(),
                "detections_per_day": per_day,
                "false_positive_rate": false_positive_rate,
                "busiest_zones": list(busiest_zones),
                "busiest_hours": [
                    {"hour": h, "count": c} for h, c in busiest_hours_sorted
                ],
            }
        )


class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: {"username": "...", "password": "..."}

    Returns a DRF auth token + the user's role, so the frontend can store
    the token (e.g. in memory / secure storage) and know immediately
    whether to render Admin or Security Viewer UI.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "username": user.username,
                "role": user.profile.role,
            }
        )


class CurrentUserView(APIView):
    """GET /api/auth/me/ — who am I, what's my role. Used on app load / page refresh."""

    permission_classes = [IsAuthenticatedRole]

    def get(self, request, *args, **kwargs):
        return Response(UserProfileSerializer(request.user.profile).data)