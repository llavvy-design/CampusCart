from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("payments/", include("payments.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/marketplace/", include("marketplace.urls")),
    path("api/community/", include("community.urls")),
    path("api/notifications/", include("notifications.urls")),
]


# Serve uploaded media files during local development only.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
