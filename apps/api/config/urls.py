"""Rutas raíz del proyecto.

Todo lo público cuelga de /api/v1/. El versionado en la URL permite publicar
una v2 sin romper un frontend ya desplegado — y en este sistema el frontend
está compilado y congelado hasta el siguiente build.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

api_v1 = [
    path("", include("core.urls")),
    path("", include("modules.site.urls")),
    path("", include("modules.projects.urls")),
    path("blog/", include("modules.blog.urls")),
    path("games/", include("modules.games.urls")),
    path("contact/", include("modules.contact.urls")),
    path("metrics/", include("modules.metrics.urls")),
]

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
]

# En desarrollo Django sirve /media/. En producción lo hace Nginx directamente
# desde el volumen: hacer pasar imágenes por Gunicorn sería malgastar hilos.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "pedrinidev.com"
admin.site.site_title = "Panel de contenido"
admin.site.index_title = "Gestión del portafolio"
