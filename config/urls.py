"""URL configuration for GIRAF Core."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from config.api import api

urlpatterns = [
    path("api/v1/", api.urls),
]

if settings.DEBUG:
    urlpatterns.insert(0, path("admin/", admin.site.urls))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # type: ignore[arg-type]
