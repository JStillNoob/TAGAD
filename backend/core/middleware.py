from django.contrib.auth import logout

from .authentication import EmailOrUsernameBackend


class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.authentication_backend = EmailOrUsernameBackend()

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not self.authentication_backend.user_can_authenticate(request.user)
        ):
            logout(request)
        return self.get_response(request)
