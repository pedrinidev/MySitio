"""Configuración de desarrollo. Nunca debe usarse en un servidor público."""

from config.env import env_bool

from .base import *
from .base import INSTALLED_APPS, REST_FRAMEWORK  # noqa: F401

DEBUG = env_bool("DJANGO_DEBUG", True)

# En desarrollo cualquier host vale: el contenedor puede resolverse como
# "api", "localhost" o por la IP de la red de Docker.
ALLOWED_HOSTS = ["*"]

# La API navegable de DRF ahorra mucho tiempo explorando endpoints,
# pero filtra información y jamás debe llegar a producción.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# El correo se imprime en la consola: nada de SMTP real mientras se desarrolla.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CORS_ALLOW_ALL_ORIGINS = True

# El webhook de reconstrucción se desactiva: no queremos disparar despliegues
# desde un portátil cada vez que se guarda un borrador de prueba.
REBUILD_WEBHOOK_ENABLED = False
