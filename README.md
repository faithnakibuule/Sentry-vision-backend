# SENTRY-VISION backend

Django 5 + Django REST Framework backend for ESP32-CAM detections, RUView radar
readings, Persons of Interest, real-time alert push, and analytics.

Core routes:

- `POST /api/auth/login/` and `POST /api/auth/refresh/`
- `GET /api/devices/`, `POST /api/devices/heartbeat/`
- `GET|POST /api/persons/`, `PATCH /api/persons/{id}/`
- `POST /api/detections/`
- `GET /api/alerts/`, `PATCH /api/alerts/{id}/`
- `POST /api/radar-readings/`
- `GET /api/analytics/summary/`
- `POST /api/logs/`
- `WS /ws/alerts/?token=<jwt_access_token>`

Device write endpoints use `X-Device-Key` or `Authorization: Api-Key <key>`.
Provision keys from Django admin or shell with:

```python
from devices.models import Device, DeviceAPIKey
device = Device.objects.get(device_id="esp32-front-door")
api_key, raw = DeviceAPIKey.issue_key(device)
print(raw)
```
