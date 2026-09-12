"""Ajuste de SQLite en cada conexión nueva.

Los PRAGMA no son persistentes: se aplican por conexión. Ponerlos aquí, en la
señal `connection_created`, garantiza que valgan tanto para Gunicorn como para
`manage.py`, los tests o una consola interactiva — y no depende de qué versión
de Django soporte la opción `init_command`.
"""

from __future__ import annotations

import logging

from django.db.backends.signals import connection_created
from django.dispatch import receiver

logger = logging.getLogger("mysite.db")

# El orden importa: WAL primero, porque cambia el modo de journaling y el
# resto de ajustes se interpretan dentro de ese modo.
SQLITE_PRAGMAS: tuple[tuple[str, str], ...] = (
    # WAL permite lecturas concurrentes mientras hay una escritura en curso.
    # Sin esto, cada guardado en el admin bloquea a todos los visitantes.
    ("journal_mode", "WAL"),
    # NORMAL hace fsync en los checkpoints, no en cada commit. En un droplet
    # con disco de red, la diferencia es de un orden de magnitud. El riesgo
    # real es perder las últimas transacciones ante un corte de energía del
    # host — asumible para un portafolio, no para datos financieros.
    ("synchronous", "NORMAL"),
    # Ante un bloqueo, esperar 5 s en vez de lanzar "database is locked".
    ("busy_timeout", "5000"),
    ("foreign_keys", "ON"),
    # 64 MB de memoria mapeada: acelera las lecturas sin coste de RSS real.
    ("mmap_size", "67108864"),
    # Negativo = kibibytes. 8 MB de caché de páginas.
    ("cache_size", "-8000"),
    # Los archivos temporales en memoria evitan tocar disco al ordenar.
    ("temp_store", "MEMORY"),
)


@receiver(connection_created)
def configure_sqlite_connection(sender, connection, **kwargs) -> None:
    """Aplica los PRAGMA de rendimiento y consistencia a cada conexión SQLite."""
    if connection.vendor != "sqlite":
        return

    with connection.cursor() as cursor:
        for pragma, value in SQLITE_PRAGMAS:
            try:
                cursor.execute(f"PRAGMA {pragma}={value};")
            except Exception:
                logger.warning("No se pudo aplicar PRAGMA %s=%s", pragma, value)
