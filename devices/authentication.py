from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import DeviceAPIKey


class DeviceAPIKeyAuthentication(BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        raw_key = request.headers.get("X-Device-Key")
        if not raw_key:
            header = request.headers.get("Authorization", "")
            if header.startswith(f"{self.keyword} "):
                raw_key = header.removeprefix(f"{self.keyword} ").strip()
        if not raw_key:
            return None

        prefix = raw_key[:8]
        candidates = DeviceAPIKey.objects.select_related("device").filter(
            key_prefix=prefix,
            is_active=True,
            device__is_active=True,
        )
        for key in candidates:
            if key.matches(raw_key):
                key.last_used_at = timezone.now()
                key.save(update_fields=["last_used_at"])
                return AnonymousUser(), key
        raise AuthenticationFailed("Invalid device API key.")
