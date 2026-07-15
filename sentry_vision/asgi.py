import os
from urllib.parse import parse_qs

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentry_vision.settings")

from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from django.contrib.auth.models import AnonymousUser  # noqa: E402
from accounts.models import User  # noqa: E402
from alerts.routing import websocket_urlpatterns  # noqa: E402
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError  # noqa: E402
from rest_framework_simplejwt.tokens import AccessToken  # noqa: E402


@database_sync_to_async
def get_user_for_token(raw_token):
    try:
        token = AccessToken(raw_token)
        return User.objects.get(id=token["user_id"], is_active=True)
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JwtAuthMiddleware:
    """Authenticate WebSocket clients with ?token=<simplejwt access token>."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        raw_token = (query.get("token") or [None])[0]
        scope["user"] = await get_user_for_token(raw_token) if raw_token else AnonymousUser()
        return await self.app(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
