"""
permissions.py
===============
Maps the frontend's two roles onto DRF permission classes.

  - Admin           -> full CRUD everywhere
  - Security Viewer -> read everywhere, PLUS may acknowledge alerts
                        (PATCH detection status), but cannot create/edit/
                        delete Suspects, Devices, or Settings.

Device-facing endpoints (burst upload, radar telemetry, heartbeat) are
deliberately NOT gated by these — they use AllowAny since the ESP32/
Arduino/radar nodes don't log in as a "user". Swap that for a
shared-secret header check before exposing the API past your LAN.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission


def _role(request):
    user = request.user
    if not (user and user.is_authenticated):
        return None
    profile = getattr(user, "profile", None)
    return profile.role if profile else None


class IsAdmin(BasePermission):
    """Full access only for the ADMIN role. Used for Settings and Device management writes."""

    def has_permission(self, request, view):
        return _role(request) == "ADMIN"


class IsAdminOrReadOnly(BasePermission):
    """
    GET/HEAD/OPTIONS -> any authenticated user (Admin or Viewer).
    POST/PUT/PATCH/DELETE -> ADMIN only.
    Used for the Persons of Interest ViewSet: Viewers can browse the
    gallery, only Admins can add/edit/delete a suspect.
    """

    def has_permission(self, request, view):
        role = _role(request)
        if role is None:
            return False
        if request.method in SAFE_METHODS:
            return True
        return role == "ADMIN"


class IsAuthenticatedRole(BasePermission):
    """
    Any logged-in user with a role (Admin or Viewer). Used for endpoints
    both roles may fully use, like acknowledging an alert or reading the
    dashboard/analytics/device list.
    """

    def has_permission(self, request, view):
        return _role(request) is not None