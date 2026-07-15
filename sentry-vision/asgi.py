"""
asgi.py
=======
Entry point when running under an ASGI server (Daphne/Uvicorn), which is
required for the WebSocket endpoints to work — `manage.py runserver`
alone (WSGI) cannot serve `ws://` connections.

Run with:  daphne -b 0.0.0.0 -p 8000 sentry_vision.asgi:application
"""
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentry_vision.settings")

# get_asgi_application() must be called before importing anything that
# touches Django models (like detection.routing), or Django's app
# registry won't be ready yet and the import will crash.
django_asgi_app = get_asgi_application()

from detection.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # AuthMiddlewareStack reads the session/token cookie so
        # `self.scope["user"]` is populated inside consumers.py, letting
        # us reject unauthenticated WebSocket connections the same way
        # DRF permission classes reject unauthenticated HTTP requests.
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)