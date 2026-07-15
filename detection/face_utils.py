"""
face_utils.py
=============
Modular facial-recognition engine for SENTRY-VISION.

Responsibilities:
  1. Extract a 128-d encoding from an arbitrary uploaded image
     (Django File/ImageField, file path, or raw bytes).
  2. Compare an incoming detection image against every SuspectProfile
     with a cached encoding, and return the closest match within a
     configurable distance tolerance.

This module intentionally has no Django REST Framework imports so it can
be unit-tested or reused (e.g. from a management command) independently
of the API layer.
"""
import io
import logging

import numpy as np

try:
    import face_recognition
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The 'face_recognition' package (and its dlib dependency) is "
        "required. Install with: pip install face_recognition dlib"
    ) from exc

from django.conf import settings

logger = logging.getLogger("sentry_vision.face_utils")

DEFAULT_TOLERANCE = getattr(settings, "FACE_MATCH_TOLERANCE", 0.6)


def _load_image_to_array(image_source):
    """
    Normalize any of the following into an RGB numpy array suitable for
    face_recognition:
      - a Django File / ImageField (has .read())
      - a file path (str / Path)
      - raw bytes
    """
    if hasattr(image_source, "read"):
        # Django's FieldFile / UploadedFile. Make sure we read from the
        # start regardless of any prior seek position.
        try:
            image_source.seek(0)
        except (AttributeError, ValueError):
            pass
        image_bytes = image_source.read()
        return face_recognition.load_image_file(io.BytesIO(image_bytes))

    if isinstance(image_source, (bytes, bytearray)):
        return face_recognition.load_image_file(io.BytesIO(image_source))

    # Assume it's a filesystem path.
    return face_recognition.load_image_file(image_source)


def get_face_encoding(image_source):
    """
    Return the 128-d encoding (numpy array) for the *first* face found in
    the given image, or None if no face is detected.

    If multiple faces are present (shouldn't happen for a suspect profile
    photo, but could for a noisy burst capture), the largest face is used
    on the assumption it's the primary subject closest to the camera.
    """
    image_array = _load_image_to_array(image_source)

    face_locations = face_recognition.face_locations(image_array)
    if not face_locations:
        return None

    if len(face_locations) > 1:
        # Pick the largest bounding box (top, right, bottom, left)
        def area(loc):
            top, right, bottom, left = loc
            return (bottom - top) * (right - left)

        face_locations = [max(face_locations, key=area)]

    encodings = face_recognition.face_encodings(
        image_array, known_face_locations=face_locations
    )
    if not encodings:
        return None

    return encodings[0]


def find_best_match(unknown_encoding, suspects, tolerance=DEFAULT_TOLERANCE):
    """
    Compare `unknown_encoding` against an iterable of SuspectProfile
    instances (each expected to expose `.get_encoding_array()`), and
    return (best_suspect, confidence) for the closest match within
    `tolerance`, or (None, None) if nothing qualifies.

    Confidence is derived as `1 - distance`, clamped to [0, 1], so it can
    be surfaced directly to the ESP32-CAM's OLED / dashboard as a
    human-readable percentage.
    """
    known_encodings = []
    known_suspects = []

    for suspect in suspects:
        encoding = suspect.get_encoding_array()
        if encoding is not None:
            known_encodings.append(encoding)
            known_suspects.append(suspect)

    if not known_encodings:
        return None, None

    distances = face_recognition.face_distance(known_encodings, unknown_encoding)
    best_index = int(np.argmin(distances))
    best_distance = float(distances[best_index])

    if best_distance > tolerance:
        return None, None

    confidence = max(0.0, min(1.0, 1.0 - best_distance))
    return known_suspects[best_index], round(confidence, 4)


def match_detection_image(image_source, suspects, tolerance=DEFAULT_TOLERANCE):
    """
    High-level convenience wrapper for the API view:
      1. Extract the encoding from the incoming burst image.
      2. Match it against `suspects`.

    Returns a dict:
      {
        "face_found": bool,
        "matched_suspect": SuspectProfile | None,
        "confidence": float | None,
      }
    """
    unknown_encoding = get_face_encoding(image_source)

    if unknown_encoding is None:
        logger.info("No face detected in uploaded detection image.")
        return {"face_found": False, "matched_suspect": None, "confidence": None}

    matched_suspect, confidence = find_best_match(
        unknown_encoding, suspects, tolerance=tolerance
    )

    return {
        "face_found": True,
        "matched_suspect": matched_suspect,
        "confidence": confidence,
    }