from django.urls import path
from . import views

urlpatterns = [
    # ESP32 endpoints
    path('upload_live/', views.upload_live, name='upload_live'),
    path('upload_sd/', views.upload_sd, name='upload_sd'),
    path('telemetry/', views.TelemetryAPIView.as_view(), name='telemetry-api'), # Add this line
    
    # React consumption endpoints
    path('stream/', views.live_stream_feed, name='live_stream_feed'),
    path('snapshots/', views.snapshot_list_api, name='snapshot_list_api'),
]