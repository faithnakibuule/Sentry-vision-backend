from django.urls import path

from .views import AnalyticsSummaryView, SensorCorrelationView

urlpatterns = [
    path("analytics/summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("analytics/correlations/", SensorCorrelationView.as_view(), name="sensor-correlations"),
]
