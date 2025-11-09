"""URL configuration for Meshup backend."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Meshup API",
        default_version="v1",
        description="Comprehensive API documentation for Meshup platform",
        terms_of_service="https://www.meshup.com/terms/",
        # contact=openapi.Contact(email="api@meshup.com"),
        # license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    url=settings.SWAGGER_API_BASE_URL,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.auth.urls")),
    path("api/v1/users/", include("apps.users.urls")),
    path("api/v1/servers/", include("apps.servers.urls")),
    path("api/v1/channels/", include("apps.channels.urls")),
    path("api/v1/messages/", include("apps.messages.urls")),
    path("api/v1/tasks/", include("apps.tasks.urls")),
    path("api/v1/notes/", include("apps.notes.urls")),
    path("api/v1/events/", include("apps.events.urls")),
    path("api/v1/polls/", include("apps.polls.urls")),
    path("api/v1/settings/", include("apps.settings.urls")),
    path("api/v1/calls/", include("apps.calls.urls")),
    path("api/v1/activity/", include("apps.activity.urls")),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
