"""Configuración de producción.

Este módulo es deliberadamente estricto: si algo esencial falta o parece
inseguro, el proceso **no arranca**. Un fallo al desplegar es barato; un
servidor público con DEBUG activado, no.
"""

from django.core.exceptions import ImproperlyConfigured

from config.env import env, env_bool, env_list

from .base import *
from .base import BASE_DIR, MIDDLEWARE, SECRET_KEY  # noqa: F401

DEBUG = False

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS es obligatorio en producción. "
        "Ejemplo: pedrinidev.com,www.pedrinidev.com"
    )

# ─────────────── Comprobaciones de arranque ───────────────
# Barreras contra el error humano, no contra un atacante: existen para que
# un despliegue apurado no publique la configuración de ejemplo.

if len(SECRET_KEY) < 32 or "cambiame" in SECRET_KEY.lower():
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY sigue siendo el valor de ejemplo o es demasiado corta. "
        "Generá una con: openssl rand -hex 32"
    )

if env_bool("DJANGO_DEBUG", False):
    raise ImproperlyConfigured("DJANGO_DEBUG no puede estar activado en producción.")

# ── Avisos del formulario de contacto ──────────────────────────
#
# Telegram va primero y no es capricho: DigitalOcean bloquea los puertos 25,
# 465 y 587 en sus droplets, así que SMTP guarda el mensaje y muere en un
# `timed out` que solo se ve en los registros — el peor fallo posible,
# porque parece que funciona. La API de Resend esquiva el bloqueo pero exige
# verificar el dominio; la de Telegram no exige nada y avisa en el teléfono.
#
# Se pueden poner los dos separados por comas. Ver core/notifications.py.
NOTIFY_CHANNELS = env_list("NOTIFY_CHANNELS", ["telegram"])

EMAIL_BACKEND = env("EMAIL_BACKEND", "core.email.ResendEmailBackend")

CANALES_VALIDOS = {"telegram", "email"}
if desconocidos := set(NOTIFY_CHANNELS) - CANALES_VALIDOS:
    raise ImproperlyConfigured(
        f"NOTIFY_CHANNELS tiene canales que no existen: {', '.join(sorted(desconocidos))}. "
        f"Opciones: {', '.join(sorted(CANALES_VALIDOS))}."
    )

if not NOTIFY_CHANNELS:
    raise ImproperlyConfigured(
        "NOTIFY_CHANNELS no puede quedar vacío: el formulario guardaría los "
        "mensajes sin avisar de ninguno."
    )

# Cada canal activo exige sus credenciales AL ARRANCAR. Es a propósito: un
# canal a medias no falla al configurarlo, falla el día que alguien escribe.
if "telegram" in NOTIFY_CHANNELS:
    faltan = [n for n in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID") if not env(n, "")]
    if faltan:
        raise ImproperlyConfigured(
            f"Falta {' y '.join(faltan)} con el canal de Telegram: sin eso el "
            "formulario de contacto guarda los mensajes pero no avisa de nada.\n"
            "El token lo da @BotFather; el chat, https://api.telegram.org"
            "/bot<TOKEN>/getUpdates después de escribirle al bot."
        )

if "email" in NOTIFY_CHANNELS:
    # Quien despliegue en un proveedor sin ese bloqueo puede volver a SMTP
    # poniendo EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend.
    if EMAIL_BACKEND.endswith("ResendEmailBackend") and not env("RESEND_API_KEY", ""):
        raise ImproperlyConfigured(
            "RESEND_API_KEY es obligatoria con el backend de Resend: sin ella "
            "el canal de correo no entrega nada.\n"
            "Sacá una en https://resend.com/api-keys — o quitá «email» de "
            "NOTIFY_CHANNELS si de momento te basta con Telegram."
        )
    if EMAIL_BACKEND.endswith("smtp.EmailBackend") and not env("EMAIL_HOST_PASSWORD", ""):
        raise ImproperlyConfigured(
            "EMAIL_HOST_PASSWORD es obligatorio con el backend SMTP: sin él, el "
            "canal de correo no entrega nada."
        )

if env("DJANGO_ADMIN_URL", "admin/") == "admin/":
    raise ImproperlyConfigured(
        "DJANGO_ADMIN_URL no puede quedarse en «admin/» en producción.\n"
        "El código de este proyecto es público, así que cualquiera sabe que "
        "detrás hay un admin de Django; dejarlo en la ruta por defecto lo "
        "entrega a los bots que barren /admin/ todo el día. No sustituye a "
        "la contraseña ni al límite de peticiones — solo quita el sitio de "
        "la lista de objetivos automáticos.\n"
        "Generá una ruta con: openssl rand -hex 8"
    )

# ─────────────────────── HTTPS y cabeceras ────────────────────

# Nginx termina el TLS y reenvía por HTTP. Sin esta cabecera, Django creería
# que la petición es insegura y entraría en un bucle de redirecciones.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

SECURE_HSTS_SECONDS = 31_536_000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # el admin necesita leerla desde JavaScript
CSRF_COOKIE_SAMESITE = "Lax"

# El admin es para una sola persona: dos semanas de sesión es de sobra.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ───────────────────────── Estáticos ──────────────────────────

# WhiteNoise sirve los estáticos del admin (unos pocos CSS y JS). Coordinar
# collectstatic con un volumen compartido con Nginx para eso no compensa.
MIDDLEWARE = [
    MIDDLEWARE[0],  # SecurityMiddleware siempre primero
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# ─────────────────────────── Correo ───────────────────────────


# ──────────────────────── Reconstrucción ──────────────────────

REBUILD_WEBHOOK_ENABLED = env_bool("REBUILD_WEBHOOK_ENABLED", True)
if REBUILD_WEBHOOK_ENABLED and not (
    env("GITHUB_DISPATCH_TOKEN", "") and env("GITHUB_REPOSITORY", "")
):
    raise ImproperlyConfigured(
        "El webhook de reconstrucción está activado pero faltan "
        "GITHUB_DISPATCH_TOKEN o GITHUB_REPOSITORY. Desactivalo con "
        "REBUILD_WEBHOOK_ENABLED=0 si aún no lo configuraste."
    )
