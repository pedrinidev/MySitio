from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class MetricSnapshot(models.Model):
    """Muestra puntual del estado del droplet.

    Alimenta el gráfico de las últimas 24 horas del dashboard. Se escribe cada
    5 minutos por cron y se purga a las 24 h: **288 filas como techo duro**.
    Una tabla de series temporales sin purga es la forma más silenciosa de
    llenar un disco de 10 GB.
    """

    cpu_percent = models.FloatField(_("CPU (%)"))
    mem_used_mb = models.PositiveIntegerField(_("RAM usada (MB)"))
    mem_total_mb = models.PositiveIntegerField(_("RAM total (MB)"))
    disk_used_gb = models.FloatField(_("disco usado (GB)"))
    disk_total_gb = models.FloatField(_("disco total (GB)"))
    load_1m = models.FloatField(_("carga 1 min"), default=0.0)
    uptime_seconds = models.PositiveBigIntegerField(_("uptime (s)"), default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("muestra de métricas")
        verbose_name_plural = _("muestras de métricas")

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} · CPU {self.cpu_percent:.1f}%"
