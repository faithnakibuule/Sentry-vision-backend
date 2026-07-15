"""
consumers.py
============
The WebSocket-side counterpart to views.py. Views handle request/response
HTTP; this handles the persistent push connection the frontend opens for
the Live Dashboard, Alerts table, and Radar View.

Flow:
  1. Browser connects to ws://.../ws/live/  (with its auth token/cookie).
  2. LiveFeedConsumer.connect() checks the role, then joins the shared
     "sentry_live" Channels group.
  3. Whenever a view creates/updates a DetectionLog, RadarTelemetry, or
     DeviceNode, it calls the small helper functions at the bottom of
     this file, which push a message into the "sentry_live" group.
  4. Every consumer in that group (i.e. every connected browser tab)
     receives it via the `live_event` handler and forwards it to its
     browser as JSON.

This is a fan-out pattern, not per-client filtering — all connected
dashboards see all events, same as a real NOC wallboard. If you later
need per-zone or per-device subscriptions, add a query-param-based group
name (e.g. "sentry_live_zone_<zone>") instead of one global group.
"""
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

LIVE_GROUP = "sentry_live"


class LiveFeedConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        # Reject the handshake outright if there's no authenticated
        # SENTRY-VISION user — mirrors IsAuthenticatedRole on the HTTP side.
        if user is None or not user.is_authenticated:
            await self.close(code=4401)  # 4401 = custom "unauthorized"
            return

        await self.channel_layer.group_add(LIVE_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(LIVE_GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # This is a push-only feed — the dashboard doesn't send commands
        # over the socket (acknowledging an alert is a normal PATCH
        # request, so the action is auditable via the API, not the
        # socket). Anything received is just ignored.
        pass

    async def live_event(self, event):
        """
        Handler name must be `live_event` to match `"type": "live_event"`
        sent via group_send() below (Channels routes group messages to
        the consumer method named after the "type" key).
        """
        await self.send(text_data=json.dumps(event["payload"]))


def broadcast_live_event(event_type, data):
    """
    Synchronous helper — call this from regular (non-async) Django views,
    model signals, etc. to push an event to every connected dashboard.

    Example:
        broadcast_live_event("new_detection", DetectionLogSerializer(obj).data)
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return  # channel layer not configured; fail silently in dev
    async_to_sync(channel_layer.group_send)(
        LIVE_GROUP,
        {
            "type": "live_event",
            "payload": {"type": event_type, "data": data},
        },
    )