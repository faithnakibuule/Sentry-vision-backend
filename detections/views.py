import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response

# Preserving your exact architectural imports
from accounts.permissions import IsAdminOrReadOnlyRole
from devices.authentication import DeviceAPIKeyAuthentication
from devices.permissions import IsDeviceRequest

from .models import DetectionEvent
from .serializers import DetectionEventSerializer

# Optional real-time updates (Uncomment if using Django Channels)
# from asgiref.sync import async_to_sync
# from channels.layers import get_channel_layer


class DetectionEventViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DetectionEventSerializer
    throttle_scope = "detection_ingest"

    def get_queryset(self):
        # Keeps database roundtrips fully optimized
        return DetectionEvent.objects.select_related("device", "match_result").all()

    def get_authenticators(self):
        if self.action == "create":
            return [DeviceAPIKeyAuthentication()]
        return super().get_authenticators()

    def get_permissions(self):
        if self.action == "create":
            return [IsDeviceRequest()]
        return [IsAdminOrReadOnlyRole()]

    def create(self, request, *args, **kwargs):
        """
        Unified ingestion engine that handles incoming traffic from both hardwares:
        1. Main ESP32 Node (JSON Telemetry logs)
        2. ESP32-CAM (Multipart Image Data + Face Recognition confirmation flags)
        """
        # Determine the source device profile checking the request format structure
        device_id = request.data.get("device_id") or request.POST.get("device_id", "UNKNOWN_NODE")
        
        # --- PATHWAY A: ESP32-CAM MULTIPART SNAPSHOT PROCESSING ---
        if "imageFile" in request.FILES:
            image_file = request.FILES["imageFile"]
            
            # Extract face detection boolean parameter from the multipart payload
            face_detected = request.POST.get("face_detected", "false").lower() == "true"
            
            # Generate a unique timestamped file path structure
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "FACE_MATCH_" if face_detected else "SNAP_"
            filename = f"security_snapshots/{prefix}{device_id}_{timestamp}.jpg"
            
            # Commit raw image file data directly to server media disk
            saved_path = default_storage.save(filename, ContentFile(image_file.read()))
            absolute_media_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)
            
            # Build camera notification dictionary profile
            event_tag = "FACE_VERIFIED_LOCK" if face_detected else "CAMERA_SNAP_CAPTURE"
            status_msg = f"Snapshot saved at: {saved_path}"
            
            # 📝 If you want to log this directly to your database through the serializer:
            # mutation_data = {
            #     "device": request.user.device.id, # Mapping out tracking targets
            #     "event_type": event_tag,
            #     "notes": f"Image URL: {absolute_media_url}"
            # }
            # serializer = self.get_serializer(data=mutation_data)
            # serializer.is_valid(raise_exception=True)
            # self.perform_create(serializer)
            
            print(f"📸 [ESP32-CAM Alert] Face Locked: {face_detected} | URL: {absolute_media_url}")
            
            # Real-Time Broadcast Hook Engine
            self._broadcast_to_frontend({
                "device_id": device_id,
                "event_type": event_tag,
                "face_detected": face_detected,
                "image_url": absolute_media_url,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            return Response({
                "status": "processed",
                "face_detected": face_detected,
                "image_url": absolute_media_url
            }, status=status.HTTP_201_CREATED)
            
        # --- PATHWAY B: MAIN ESP32 TELEMETRY PROCESSING ---
        else:
            event_type = request.data.get("event_type", "SECURE_HEARTBEAT")
            status_msg = request.data.get("status", "")
            
            print(f"📡 [Main Node Ingest] {event_type} | {status_msg}")
            
            # Route payload data using standard DRF serializer serialization
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            
            # Append exact live timestamp details to push metrics smoothly to web client interface
            broadcast_data = dict(serializer.data)
            broadcast_data["timestamp"] = datetime.datetime.now().isoformat()
            
            self._broadcast_to_frontend(broadcast_data)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def _broadcast_to_frontend(self, payload):
        """
        Helper channel execution routing module to immediately mirror background log events
        directly to your React frontend application dashboard views.
        """
        # try:
        #     channel_layer = get_channel_layer()
        #     async_to_sync(channel_layer.group_send)(
        #         "security_alerts",
        #         {
        #             "type": "security_broadcast",
        #             "message": payload
        #         }
        #     )
        # except Exception as e:
        #     print(f"WebSocket Broadcast omitted: {str(e)}")
        pass