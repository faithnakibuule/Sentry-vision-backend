# SENTRY-VISION backend

Django 5 + Django REST Framework backend for ESP32-CAM detections, RUView radar
readings, Persons of Interest, real-time alert push, and analytics.

Core routes:

- `POST /api/auth/login/` and `POST /api/auth/refresh/`
- `GET /api/devices/`, `POST /api/devices/heartbeat/`
- `GET|POST /api/persons/`, `PATCH /api/persons/{id}/`
- `POST /api/detections/`
- `POST /api/detections/recognize/` (ESP32-CAM multipart JPEG recognition)
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

## ESP32-CAM recognition upload

Post `multipart/form-data` to `/api/detections/recognize/` with the JPEG in
the `image` field. The endpoint authenticates the device using `X-Device-Key`;
send the provisioned device ID in `X-Camera-ID` as an additional guard. An
optional `trigger_source` field accepts `motion`, `ultrasonic`, `radar`, or
`manual` and defaults to `motion`.

The response is JSON and includes `status` (`matched`, `unmatched`, or
`failed`), `subject`, `confidence`, `face_distance`, and `error`. The complete,
buffer-safe ESP32-CAM upload function is in
[`firmware/esp32_cam_face_upload.ino`](firmware/esp32_cam_face_upload.ino).
The server image must install the `face-recognition` requirement (and its dlib
build dependencies) for real face encoding and matching.
