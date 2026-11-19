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
