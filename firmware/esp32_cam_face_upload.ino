/*
 * Multipart JPEG uploader for the Django endpoint:
 * POST https://<server>/api/detections/recognize/
 *
 * Initialize Wi-Fi and esp_camera before calling uploadCameraFrame().  The
 * camera must be configured with PIXFORMAT_JPEG.  For HTTPS, pass a configured
 * WiFiClientSecure instance (with setCACert() or a development-only
 * setInsecure()) because WiFiClientSecure inherits from WiFiClient.
 */
#include <Arduino.h>
#include <HTTPClient.h>
#include <limits.h>
#include <WiFiClient.h>
#include "esp_camera.h"

class MultipartJpegStream : public Stream {
 public:
  MultipartJpegStream(const String &prefix, const uint8_t *jpeg, size_t jpegLength,
                      const String &suffix)
      : prefix_(prefix), jpeg_(jpeg), jpegLength_(jpegLength), suffix_(suffix) {}

  int available() override {
    const size_t remaining = size() - position_;
    return remaining > INT_MAX ? INT_MAX : static_cast<int>(remaining);
  }

  int read() override {
    if (position_ >= size()) return -1;
    return byteAt(position_++);
  }

  int peek() override {
    return position_ >= size() ? -1 : byteAt(position_);
  }

  void flush() override {}
  size_t write(uint8_t) override { return 0; }
  size_t size() const { return prefix_.length() + jpegLength_ + suffix_.length(); }

 private:
  int byteAt(size_t position) const {
    if (position < prefix_.length()) return static_cast<uint8_t>(prefix_[position]);
    position -= prefix_.length();
    if (position < jpegLength_) return jpeg_[position];
    position -= jpegLength_;
    return static_cast<uint8_t>(suffix_[position]);
  }

  const String &prefix_;
  const uint8_t *jpeg_;
  size_t jpegLength_;
  const String &suffix_;
  size_t position_ = 0;
};

bool uploadCameraFrame(
    WiFiClient &client,
    const char *endpoint,
    const char *deviceApiKey,
    const char *cameraId,
    const char *triggerSource = "motion") {
  camera_fb_t *frame = esp_camera_fb_get();
  if (frame == nullptr) {
    Serial.println("Camera capture failed");
    return false;
  }

  // This stream avoids allocating a second buffer as large as the JPEG.
  const String boundary = "ESP32CamBoundary7MA4YWxkTrZu0gW";
  String prefix;
  prefix.reserve(300);
  prefix += "--" + boundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"trigger_source\"\r\n\r\n";
  prefix += String(triggerSource) + "\r\n";
  prefix += "--" + boundary + "\r\n";
  prefix += "Content-Disposition: form-data; name=\"image\"; filename=\"frame.jpg\"\r\n";
  prefix += "Content-Type: image/jpeg\r\n\r\n";
  const String suffix = "\r\n--" + boundary + "--\r\n";

  MultipartJpegStream body(prefix, frame->buf, frame->len, suffix);
  HTTPClient http;
  http.setTimeout(15000);
  if (!http.begin(client, endpoint)) {
    Serial.println("Could not start HTTP request");
    esp_camera_fb_return(frame);
    return false;
  }

  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  http.addHeader("X-Device-Key", deviceApiKey);
  http.addHeader("X-Camera-ID", cameraId);
  http.addHeader("Accept", "application/json");

  const int statusCode = http.sendRequest("POST", &body, body.size());
  const String response = statusCode > 0 ? http.getString() : http.errorToString(statusCode);
  Serial.printf("recognition HTTP %d: %s\n", statusCode, response.c_str());

  http.end();
  esp_camera_fb_return(frame);

  // 201 contains a complete matched, unmatched, or failed JSON result.
  return statusCode == HTTP_CODE_CREATED;
}

// Example (after Wi-Fi and camera initialization):
// WiFiClient client;
// uploadCameraFrame(client, "http://192.168.1.50:8000/api/detections/recognize/",
//                   "<raw-device-api-key>", "esp32-front-door");
