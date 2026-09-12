from rest_framework import serializers

from modules.metrics.models import MetricSnapshot


class MetricSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricSnapshot
        fields = (
            "cpu_percent",
            "mem_used_mb",
            "mem_total_mb",
            "disk_used_gb",
            "disk_total_gb",
            "load_1m",
            "created_at",
        )
