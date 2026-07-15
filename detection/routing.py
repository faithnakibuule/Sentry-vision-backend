"""
routing.py
==========
WebSocket equivalent of urls.py. Referenced by sentry_vision/asgi.py.

ws/live/  -> pushes two event types to every connected dashboard client:
    { "type": "new_detection",   "data": {...DetectionLogSerializer...} }
    { "type": "detection_status", "data": {...DetectionLogSerializer...} }
    { "type": "radar_update",    "data": {...RadarTelemetrySerializer...} }
    { "type": "device_status",   "data": {...DeviceNodeSerializer...} }

One shared stream keeps the frontend's WebSocket wiring simple (one
socket, dispatch on `type`) rather than juggling four separate sockets
for Live Dashboard / Alerts / Radar View / Device Health.
"""
from django.urls import re_path

from .consumers import LiveFeedConsumer

websocket_urlpatterns = [
    re_path(r"ws/live/$", LiveFeedConsumer.as_asgi()),
]