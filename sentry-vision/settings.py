"""
Django settings for SENTRY-VISION project.
Embedded multi-modal surveillance backend (ESP32-CAM + RUView radar).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-only-change-me-in-production"

# ESP32-CAM and radar nodes will be on the LAN during dev, so DEBUG stays on
# and ALLOWED_HOSTS is permissive. Lock this down before deploying.
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",  # token auth for the dashboard's Admin/Viewer login
    "channels",                  # WebSocket support for the live alert feed
    "detection",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sentry_vision.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sentry_vision.wsgi.application"
ASGI_APPLICATION = "sentry_vision.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kampala"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Media (suspect profile photos + detection burst images)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Token auth for dashboard users logging in as Admin/Viewer (obtained
    # via POST /api/auth/login/). Device-facing views (upload/telemetry/
    # heartbeat) explicitly override this with AllowAny in their own
    # `permission_classes`, since edge hardware doesn't hold a user token.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# --- SENTRY-VISION specific settings ---
# Distance tolerance for face_recognition.compare_faces / face_distance.
# Lower = stricter match. 0.6 is the library's own recommended default.
# (Also mirrored in the SystemSettings DB row so it's editable from the
# Settings page without a redeploy — see detection/models.py.)
FACE_MATCH_TOLERANCE = 0.6

# Channels — in-memory layer is fine for a single dev-server process.
# For production (multiple workers, or Daphne behind nginx) swap this for
# channels_redis.core.RedisChannelLayer so all workers share one bus.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}