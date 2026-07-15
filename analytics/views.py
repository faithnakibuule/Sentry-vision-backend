from django.db.models import Avg, Count
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alerts.models import Alert
from detections.models import DetectionEvent, FacialMatchResult
from radar.models import RadarReading


class AnalyticsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        since = timezone.now() - timezone.timedelta(days=days)
        detections = DetectionEvent.objects.filter(timestamp__gte=since)
        matches = FacialMatchResult.objects.filter(detection__timestamp__gte=since)

        matched_count = matches.filter(status=FacialMatchResult.Status.MATCHED).count()
        unmatched_count = matches.filter(status=FacialMatchResult.Status.UNMATCHED).count()
        false_positive_rate = unmatched_count / matched_count if matched_count else None

        return Response(
            {
                "range_days": days,
                "detections_per_day": list(
                    detections.annotate(day=TruncDate("timestamp"))
                    .values("day")
                    .annotate(count=Count("id"))
                    .order_by("day")
                ),
                "detections_by_zone": list(
                    detections.values("zone").annotate(count=Count("id")).order_by("-count")
                ),
                "false_positive_rate": false_positive_rate,
                "alert_counts_by_severity": list(
                    Alert.objects.filter(created_at__gte=since)
                    .values("severity")
                    .annotate(count=Count("id"))
                    .order_by("severity")
                ),
                "busiest_zones": list(
                    detections.values("zone").annotate(count=Count("id")).order_by("-count")[:10]
                ),
                "busiest_times": list(
                    detections.annotate(hour=ExtractHour("timestamp"))
                    .values("hour")
                    .annotate(count=Count("id"))
                    .order_by("-count")[:10]
                ),
                "average_radar_heart_rate": RadarReading.objects.filter(timestamp__gte=since).aggregate(
                    value=Avg("heart_rate_bpm")
                )["value"],
            }
        )


class SensorCorrelationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        seconds = int(request.query_params.get("window_seconds", 5))
        limit = int(request.query_params.get("limit", 50))
        rows = []
        for detection in DetectionEvent.objects.select_related("device").order_by("-timestamp")[:limit]:
            start = detection.timestamp - timezone.timedelta(seconds=seconds)
            end = detection.timestamp + timezone.timedelta(seconds=seconds)
            readings = RadarReading.objects.filter(zone=detection.zone, timestamp__gte=start, timestamp__lte=end)
            rows.append(
                {
                    "detection_id": detection.id,
                    "zone": detection.zone,
                    "timestamp": detection.timestamp,
                    "radar_readings": list(
                        readings.values(
                            "id",
                            "presence_detected",
                            "heart_rate_bpm",
                            "height_estimate_cm",
                            "movement_pattern",
                            "timestamp",
                        )
                    ),
                }
            )
        return Response(rows)
