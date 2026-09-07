from rest_framework.permissions import BasePermission


class CanManageUsers(BasePermission):
    message = 'You do not have permission to manage users.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and user.role in (user.Role.SYSTEM_ADMIN, user.Role.ORG_ADMIN)
        )


class CanAccessClassManagement(BasePermission):
    message = 'You do not have permission to modify classes.'

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return user.role in user.Role.values
        return user.role in (user.Role.SYSTEM_ADMIN, user.Role.ORG_ADMIN)
