"""Lectura del estado real del droplet.

El problema que resuelve este módulo: `psutil` dentro de un contenedor mide el
**contenedor**, no la máquina. Un dashboard que informa de la RAM del
contenedor y la presenta como la del servidor es decoración, no monitorización.

La solución es montar los sistemas de archivos virtuales del host en modo
lectura y redirigir psutil hacia ellos:

    volumes:
      - /proc:/host/proc:ro
      - /:/host/root:ro

    HOST_PROC_PATH=/host/proc
    HOST_ROOT_PATH=/host/root

En desarrollo (macOS no tiene /proc) `HOST_PROC_PATH` queda vacío y psutil
mide el contenedor. Es la degradación correcta: los números locales no
significan nada de todos modos.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import psutil
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from modules.metrics.models import MetricSnapshot

logger = logging.getLogger("mysite.metrics")

_CACHE_KEY = "metrics:live"
_MB = 1024 * 1024
_GB = 1024 * 1024 * 1024

_procfs_configured = False


def _configure_procfs() -> None:
    """Apunta psutil al /proc del host. Idempotente."""
    global _procfs_configured
    if _procfs_configured:
        return
    host_proc = settings.HOST_PROC_PATH
    if host_proc:
        psutil.PROCFS_PATH = host_proc
        logger.info("psutil leerá las métricas del host desde %s", host_proc)
    _procfs_configured = True


def _read_uptime() -> int:
    """Uptime en segundos.

    `psutil.boot_time()` con PROCFS_PATH redirigido devuelve el arranque del
    host, que es lo que queremos mostrar: reiniciar un contenedor no debería
    poner el uptime del servidor a cero.
    """
    try:
        return max(0, int(time.time() - psutil.boot_time()))
    except Exception:
        return 0


def collect() -> dict[str, Any]:
    """Toma una medición fresca del sistema.

    Cada lectura está aislada: si `getloadavg` no está disponible en la
    plataforma, el resto de métricas siguen sirviéndose. Un dashboard con un
    dato menos es infinitamente mejor que un 500.
    """
    _configure_procfs()

    # interval=None devuelve el porcentaje desde la llamada anterior, sin
    # bloquear. Con interval=1 cada petición congelaría un hilo de Gunicorn
    # durante un segundo entero — inaceptable con solo 8 hilos.
    cpu_percent = psutil.cpu_percent(interval=None)

    memory = psutil.virtual_memory()

    try:
        disk = psutil.disk_usage(settings.HOST_ROOT_PATH or "/")
    except OSError:
        logger.warning("No se pudo leer el disco en %s", settings.HOST_ROOT_PATH)
        disk = psutil.disk_usage("/")

    try:
        load_1m = psutil.getloadavg()[0]
    except (OSError, AttributeError):
        load_1m = 0.0

    return {
        "cpu_percent": round(cpu_percent, 1),
        "memory": {
            "used_mb": int((memory.total - memory.available) / _MB),
            "total_mb": int(memory.total / _MB),
            "percent": round(memory.percent, 1),
        },
        "disk": {
            "used_gb": round(disk.used / _GB, 2),
            "total_gb": round(disk.total / _GB, 2),
            "percent": round(disk.percent, 1),
        },
        "load_1m": round(load_1m, 2),
        "uptime_seconds": _read_uptime(),
        "measured_at": timezone.now().isoformat(),
    }


def get_live_metrics() -> dict[str, Any]:
    """Métricas actuales, cacheadas unos segundos.

    Sin caché, cien visitantes con el dashboard abierto generarían cien
    lecturas de /proc por segundo. Con 10 s de ventana son 6 por minuto —
    y el dashboard sigue pareciendo igual de vivo.
    """
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    metrics = collect()
    cache.set(_CACHE_KEY, metrics, timeout=settings.METRICS_CACHE_SECONDS)
    return metrics


def take_snapshot() -> MetricSnapshot:
    """Guarda una muestra para el histórico."""
    data = collect()
    return MetricSnapshot.objects.create(
        cpu_percent=data["cpu_percent"],
        mem_used_mb=data["memory"]["used_mb"],
        mem_total_mb=data["memory"]["total_mb"],
        disk_used_gb=data["disk"]["used_gb"],
        disk_total_gb=data["disk"]["total_gb"],
        load_1m=data["load_1m"],
        uptime_seconds=data["uptime_seconds"],
    )


def purge_old_snapshots() -> int:
    """Borra las muestras fuera de la ventana de retención."""
    cutoff = timezone.now() - timezone.timedelta(hours=settings.METRICS_RETENTION_HOURS)
    deleted, _ = MetricSnapshot.objects.filter(created_at__lt=cutoff).delete()
    return deleted
