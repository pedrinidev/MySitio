from __future__ import annotations

from django.utils import timezone
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from modules.metrics import services
from modules.metrics.models import MetricSnapshot
from modules.metrics.serializers import MetricSnapshotSerializer


@api_view(["GET"])
def live_metrics(request) -> Response:
    """Estado actual del droplet.

    Se exponen porcentajes y totales agregados, nunca la lista de procesos,
    rutas del sistema de archivos ni el nombre del host: eso no le aporta nada
    al visitante y sí a quien esté haciendo reconocimiento.
    """
    return Response(services.get_live_metrics())


class MetricHistoryView(generics.ListAPIView):
    """Serie temporal para el gráfico del dashboard."""

    serializer_class = MetricSnapshotSerializer
    pagination_class = None

    def get_queryset(self):
        try:
            hours = min(int(self.request.query_params.get("hours", 24)), 24)
        except ValueError:
            hours = 24
        since = timezone.now() - timezone.timedelta(hours=max(hours, 1))
        return MetricSnapshot.objects.filter(created_at__gte=since).order_by("created_at")
