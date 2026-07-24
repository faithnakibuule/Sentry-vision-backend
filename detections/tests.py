from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase

from devices.models import Device, DeviceAPIKey
from persons.models import PersonOfInterest


class CameraRecognitionViewTests(APITestCase):
    def setUp(self):
        self.device = Device.objects.create(
            device_id="esp32-front-door",
            device_type=Device.Type.ESP32_CAM,
            zone="front-door",
        )
        _, self.raw_key = DeviceAPIKey.issue_key(self.device, "camera")
        self.url = reverse("camera-recognize")
        self.headers = {
            "HTTP_X_DEVICE_KEY": self.raw_key,
            "HTTP_X_CAMERA_ID": self.device.device_id,
        }

    @patch("detections.views.compare_encoding")
    @patch("detections.views.get_face_encoding")
    def test_returns_match_for_multipart_image(self, get_face_encoding, compare_encoding):
        person = PersonOfInterest.objects.create(full_name="Ada Lovelace", threat_level="high")
        get_face_encoding.return_value = object()
        compare_encoding.return_value = (person, 0.92, 0.08)

        response = self.client.post(
            self.url,
            {"image": SimpleUploadedFile("frame.jpg", b"jpeg", content_type="image/jpeg")},
            format="multipart",
            **self.headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "matched")
        self.assertTrue(response.data["matched"])
        self.assertEqual(response.data["subject"]["id"], person.id)
        self.assertEqual(response.data["face_distance"], 0.08)

    @patch("detections.views.get_face_encoding", return_value=None)
    def test_returns_unmatched_when_no_face_is_found(self, _get_face_encoding):
        response = self.client.post(
            self.url,
            {"image": SimpleUploadedFile("frame.jpg", b"jpeg", content_type="image/jpeg")},
            format="multipart",
            **self.headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "unmatched")
        self.assertEqual(response.data["error"], "No face detected in image.")

    def test_rejects_camera_id_that_does_not_match_key(self):
        response = self.client.post(
            self.url,
            {"image": SimpleUploadedFile("frame.jpg", b"jpeg", content_type="image/jpeg")},
            format="multipart",
            HTTP_X_DEVICE_KEY=self.raw_key,
            HTTP_X_CAMERA_ID="different-camera",
        )

        self.assertEqual(response.status_code, 403)
