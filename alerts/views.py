from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import is_admin, is_role_user

from .broadcast import broadcast_alert_event
from .models import Alert
from .serializers import AlertAcknowledgeSerializer, AlertSerializer


class AlertViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = AlertSerializer

    def get_queryset(self):
        qs = Alert.objects.select_related("detection", "person", "acknowledged_by").all()
        acknowledged = self.request.query_params.get("acknowledged")
        severity = self.request.query_params.get("severity")
        if acknowledged is not None:
            qs = qs.filter(acknowledged=acknowledged.lower() in {"1", "true", "yes"})
        if severity:
            qs = qs.filter(severity=severity)
        return qs

    def has_update_permission(self):
        return is_role_user(self.request.user)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Use PATCH to acknowledge alerts."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        if not self.has_update_permission():
            return Response({"detail": "Authentication credentials were not provided."}, status=403)
        alert = self.get_object()
        serializer = AlertAcknowledgeSerializer(alert, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        alert = serializer.save()
        payload = AlertSerializer(alert).data
        broadcast_alert_event("alert.updated", payload)
        return Response(payload)

    @action(detail=False, methods=["post"])
    def create_manual(self, request):
        if not is_admin(request.user):
            return Response({"detail": "Admin role required."}, status=403)
        alert = Alert.objects.create(
            source=Alert.Source.SUSPICIOUS_BEHAVIOR,
            severity=request.data.get("severity", Alert.Severity.MEDIUM),
            message=request.data.get("message", "Manual SENTRY-VISION alert."),
        )
        return Response(AlertSerializer(alert).data, status=201)
