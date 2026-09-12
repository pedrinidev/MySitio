from django.urls import path

from modules.metrics import views

urlpatterns = [
    path("live/", views.live_metrics, name="metrics-live"),
    path("history/", views.MetricHistoryView.as_view(), name="metrics-history"),
]
