from rest_framework.permissions import BasePermission


class CanManageUsers(BasePermission):
    message = 'You do not have permission to manage users.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and user.role in (user.Role.SYSTEM_ADMIN, user.Role.ORG_ADMIN)
        )
