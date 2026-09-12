from django.contrib import admin

from modules.metrics.models import MetricSnapshot


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ("created_at", "cpu_percent", "mem_used_mb", "disk_used_gb", "load_1m")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
