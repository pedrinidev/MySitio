"""Configuración común a todos los entornos.

Nunca se usa directamente: `dev.py` y `prod.py` la extienden. Esa separación es
deliberada — un único settings.py con `if DEBUG` acaba, tarde o temprano,
desplegando con DEBUG activado.
"""

from __future__ import annotations

from pathlib import Path

from config.env import env, env_bool, env_int, env_list

# apps/api/config/settings/base.py → apps/api
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Raíz del monorepo (para localizar .env en ejecuciones fuera de Docker)
REPO_ROOT = BASE_DIR.parent.parent

# Carga .env solo si existe. En Docker las variables llegan por env_file y
# este bloque no hace nada.
try:
    from dotenv import load_dotenv

    for candidate in (REPO_ROOT / ".env", BASE_DIR / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            break
except ImportError:  # pragma: no cover
    pass

# ─────────────────────────── Núcleo ───────────────────────────

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False  # cada entorno decide; el valor seguro es el que manda por defecto
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# La URL del admin es configurable para no dejarla en la ruta obvia en
# producción. No es seguridad real, pero elimina el 99 % del ruido de bots.
ADMIN_URL = env("DJANGO_ADMIN_URL", "admin/")

# ──────────────────────── Aplicaciones ────────────────────────

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS = [
    "core",
    "modules.site",
    "modules.projects",
    "modules.blog",
    "modules.games",
    "modules.contact",
    "modules.metrics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    # El PRIMERO, y no por capricho: corrige la cabecera Host del healthcheck
    # local antes de que SecurityMiddleware llame a get_host() y reviente.
    # Ver core/middleware.py para por qué no basta con ampliar ALLOWED_HOSTS.
    "core.middleware.LoopbackHealthHostMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # CORS debe ir lo más arriba posible: tiene que poder responder a las
    # peticiones preflight antes de que otro middleware las rechace.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ───────────────────────── Base de datos ──────────────────────

# SQLite en modo WAL. Los PRAGMA se aplican en core/db.py mediante la señal
# connection_created, no aquí: así se ejecutan en cada conexión nueva y el
# comportamiento no depende de la versión de Django.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env("DATABASE_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {
            # IMMEDIATE evita el clásico "database is locked" cuando dos
            # transacciones de escritura se solapan: el bloqueo se toma al
            # abrir, no al primer INSERT.
            "transaction_mode": "IMMEDIATE",
            "timeout": 5,
        },
    }
}

# ───────────────────────────── Caché ──────────────────────────

CACHES = {
    # Caché de proceso para datos efímeros (métricas). Cada worker de Gunicorn
    # tiene la suya: con 2 workers medimos el host 2 veces por ventana en vez
    # de una. Es un coste aceptable y ahorra los ~40 MB de Redis.
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mysite-default",
        "TIMEOUT": 300,
    },
    # El throttling SÍ necesita estado compartido: un límite de 3 mensajes por
    # hora que en realidad son 3 por worker no es un límite. Va a SQLite.
    "throttle": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_throttle",
        "TIMEOUT": 3600,
    },
}

# ────────────────────── Contraseñas y auth ────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─────────────────── Internacionalización ─────────────────────

LANGUAGE_CODE = "es"
LANGUAGES = [("es", "Español"), ("en", "English")]
DEFAULT_LANGUAGE = "es"
SUPPORTED_LANGUAGES = ("es", "en")

TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

# ──────────────────── Archivos estáticos y media ──────────────

STATIC_URL = "/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", str(BASE_DIR / "staticfiles")))
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

# Base pública desde la que el NAVEGADOR alcanza /media/. Vacía en producción:
# allí la API y los archivos cuelgan del mismo dominio y basta la cabecera Host.
# Ver core/serializers.py, AbsoluteImageField.
PUBLIC_MEDIA_BASE_URL = env("PUBLIC_MEDIA_BASE_URL", "")

# Tope de subida: 5 MB. Suficiente para portadas de proyectos y muy por debajo
# de lo que aguanta un droplet de 512 MB sin empezar a usar disco.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ────────────────────── Django REST Framework ─────────────────

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # Lista VACÍA a propósito, no un olvido.
    #
    # Sin esto DRF aplica su valor por defecto, SessionAuthentication, que
    # exige un token CSRF en cuanto la petición trae una cookie de sesión.
    # Esta API es enteramente anónima —ninguna vista mira `request.user` ni
    # pide permisos— así que esa autenticación no aportaba nada y sí rompía
    # algo: quien tuviera abierta la sesión del admin recibía 403 al usar el
    # formulario de contacto o al contar una visita del blog.
    #
    # Lo pernicioso es a quién le fallaba. Un visitante cualquiera no tiene
    # sesión y nunca lo notaba; el único que lo sufría era el administrador,
    # es decir, la persona que prueba el sitio. Parecía roto para el dueño y
    # funcionaba para todos los demás.
    #
    # El admin de Django NO se ve afectado: es una vista normal y conserva
    # su propia sesión y su propio CSRF.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.DefaultPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": ["core.throttling.SharedAnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "contact": "3/hour",
        "game-session": "30/hour",
        "score": "20/hour",
        "search": "30/min",
    },
    "UNAUTHENTICATED_USER": None,
}

# ───────────────────────────── CORS ───────────────────────────

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", ["http://localhost:4321"])
CORS_ALLOW_CREDENTIALS = False  # la API es pública y sin sesión: no hacen falta cookies
CORS_ALLOW_METHODS = ["GET", "POST", "OPTIONS"]
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", ["http://localhost:4321"])

# ──────────────────────────── Correo ──────────────────────────

EMAIL_HOST = env("EMAIL_HOST", "smtp.zoho.com")
EMAIL_PORT = env_int("EMAIL_PORT", 465)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", True)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")

# Clave de la API de Resend, usada por core.email.ResendEmailBackend.
# Ver ese archivo para por qué no se usa SMTP en producción.
RESEND_API_KEY = env("RESEND_API_KEY", "")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "contacto@pedrinidev.com")
CONTACT_TO_EMAIL = env("CONTACT_TO_EMAIL", "pedrinidevs@gmail.com")
EMAIL_TIMEOUT = 10  # sin esto, un SMTP colgado bloquea un hilo de Gunicorn

# ──────────────────────────── Avisos ──────────────────────────

# Canales por los que se avisa de un mensaje de contacto, separados por
# comas: "telegram", "email", o ambos. Ver core/notifications.py.
#
# El valor por defecto es "email" para que las pruebas y el entorno de
# desarrollo sigan usando el backend en memoria de Django y `mail.outbox`
# siga siendo observable. Producción lo cambia en su .env.
NOTIFY_CHANNELS = env_list("NOTIFY_CHANNELS", ["email"])

# Credenciales del bot de Telegram, usadas por core.notifications.
# El token se saca hablando con @BotFather; el chat es el de la conversación
# donde debe llegar el aviso.
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID", "")

# ───────────────── Ajustes propios de la aplicación ───────────

# Sal para hashear IPs. No se almacena ninguna IP en claro en la base de datos.
IP_HASH_SALT = env("IP_HASH_SALT", SECRET_KEY)

# Firma de los tokens de sesión de los juegos.
GAME_TOKEN_SECRET = env("GAME_TOKEN_SECRET", SECRET_KEY)
GAME_TOKEN_TTL_SECONDS = env_int("GAME_TOKEN_TTL_SECONDS", 1800)

# Formulario de contacto: un envío en menos de este tiempo es un bot.
CONTACT_MIN_ELAPSED_MS = env_int("CONTACT_MIN_ELAPSED_MS", 3000)

# Token que exime del límite de peticiones al proceso de build.
#
# Astro prerenderiza el sitio entero consultando esta API: unas 30 peticiones
# en pocos segundos desde una sola IP, que es exactamente el patrón que el
# límite anónimo (60/min) existe para frenar. Sin esta exención, el build de
# GitHub Actions recibe 429 y el despliegue falla.
#
# Vacío = sin exención (comportamiento por defecto en desarrollo).
BUILD_API_TOKEN = env("BUILD_API_TOKEN", "")

# Reconstrucción del sitio estático al publicar contenido.
GITHUB_DISPATCH_TOKEN = env("GITHUB_DISPATCH_TOKEN", "")
GITHUB_REPOSITORY = env("GITHUB_REPOSITORY", "")
REBUILD_WEBHOOK_ENABLED = env_bool("REBUILD_WEBHOOK_ENABLED", False)

# Métricas: rutas del host montadas en solo lectura dentro del contenedor.
# Vacío = medir el propio contenedor (lo normal en desarrollo).
HOST_PROC_PATH = env("HOST_PROC_PATH", "")
HOST_ROOT_PATH = env("HOST_ROOT_PATH", "/")
METRICS_CACHE_SECONDS = env_int("METRICS_CACHE_SECONDS", 10)
METRICS_RETENTION_HOURS = env_int("METRICS_RETENTION_HOURS", 24)

PUBLIC_SITE_URL = env("PUBLIC_SITE_URL", "http://localhost:4321")

# ──────────────────────────── Logging ─────────────────────────

LOG_LEVEL = env("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        # Siempre a stdout: en Docker, los logs los recoge el runtime.
        # Escribir a un archivo dentro del contenedor es perderlos.
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "propagate": False, "handlers": ["console"]},
        "mysite": {"level": LOG_LEVEL, "propagate": False, "handlers": ["console"]},
    },
}
