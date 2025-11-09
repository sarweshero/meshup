"""ASGI configuration for Meshup supporting HTTP and WebSocket protocols."""
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import re_path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# Initialise Django's ASGI application before importing consumers
django_asgi_app = get_asgi_application()

from apps.calls.consumers import CallConsumer  # noqa: E402
from apps.events.consumers import EventConsumer  # noqa: E402
from apps.messages.consumers import DirectMessageConsumer, MessageConsumer  # noqa: E402
from apps.presence.consumers import PresenceConsumer  # noqa: E402


websocket_urlpatterns = [
	re_path(r"^ws/channels/(?P<channel_id>[\w-]+)/$", MessageConsumer.as_asgi()),
	re_path(r"^ws/dm/(?P<dm_channel_id>[\w-]+)/$", DirectMessageConsumer.as_asgi()),
	re_path(r"^ws/events/(?P<event_id>[\w-]+)/$", EventConsumer.as_asgi()),
	re_path(r"^ws/presence/(?P<server_id>[\w-]+)/$", PresenceConsumer.as_asgi()),
	re_path(r"^ws/calls/(?P<call_id>[\w-]+)/$", CallConsumer.as_asgi()),
]


application = ProtocolTypeRouter(
	{
		"http": django_asgi_app,
		"websocket": AllowedHostsOriginValidator(
			AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
		),
	}
)
