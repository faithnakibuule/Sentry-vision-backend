from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_admin(user):
    return bool(user and user.is_authenticated and getattr(user, "is_sentry_admin", False))


def is_role_user(user):
    return bool(user and user.is_authenticated and getattr(user, "role", None))


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)


class IsAdminOrReadOnlyRole(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return is_role_user(request.user)
        return is_admin(request.user)
