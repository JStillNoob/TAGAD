from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identity = username or kwargs.get(user_model.USERNAME_FIELD)
        if not identity or not password:
            return None

        try:
            user = user_model.objects.get(
                Q(username__iexact=identity) | Q(email__iexact=identity),
            )
        except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
            # Keep password-hashing work similar when an identity does not resolve.
            user_model().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        organization = user.organization
        return (
            super().user_can_authenticate(user)
            and user.status == user.Status.ACTIVE
            and (organization is None or organization.status == organization.Status.ACTIVE)
        )

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model._default_manager.select_related('organization').get(pk=user_id)
        except user_model.DoesNotExist:
            return None
