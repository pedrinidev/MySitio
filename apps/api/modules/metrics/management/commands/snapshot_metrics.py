"""Toma una muestra de métricas y purga las antiguas.

Se ejecuta desde el cron del host cada 5 minutos:

    */5 * * * * docker compose -f /srv/mysite/compose.prod.yml exec -T api \\
        python manage.py snapshot_metrics

Guardar y purgar en el mismo comando es intencional: así la limpieza no puede
quedar sin programar y dejar la tabla creciendo indefinidamente.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.metrics import services


class Command(BaseCommand):
    help = "Registra una muestra de métricas del servidor y purga las caducadas."

    def handle(self, *args, **options) -> None:
        snapshot = services.take_snapshot()
        deleted = services.purge_old_snapshots()

        self.stdout.write(
            self.style.SUCCESS(
                f"Muestra registrada: CPU {snapshot.cpu_percent}% · "
                f"RAM {snapshot.mem_used_mb}/{snapshot.mem_total_mb} MB · "
                f"purgadas {deleted}"
            )
        )
