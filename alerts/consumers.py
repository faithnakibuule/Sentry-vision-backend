import json

from channels.generic.websocket import AsyncWebsocketConsumer

from .broadcast import ALERTS_GROUP


class AlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add(ALERTS_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(ALERTS_GROUP, self.channel_name)

    async def alert_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
