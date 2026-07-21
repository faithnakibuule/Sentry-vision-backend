from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

ALERTS_GROUP = "alerts"


def broadcast_alert_event(event_type, data):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            ALERTS_GROUP,
            {"type": "alert.event", "payload": {"type": event_type, "data": data}},
        )
    except Exception:
        # Allow demo data seeding and offline startup when Redis is not available.
        return
