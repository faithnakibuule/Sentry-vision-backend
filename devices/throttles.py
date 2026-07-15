from rest_framework.throttling import ScopedRateThrottle


class DeviceScopedRateThrottle(ScopedRateThrottle):
    def get_cache_key(self, request, view):
        if getattr(view, "throttle_scope", None) != self.scope:
            return None
        device_key = getattr(request, "auth", None)
        device = getattr(device_key, "device", None)
        if device is None:
            return None
        ident = device.device_id
        return self.cache_format % {"scope": self.scope, "ident": ident}
