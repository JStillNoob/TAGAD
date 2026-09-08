from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SystemLog, User
from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetTokenSerializer,
)
from .views import _request_ip


GENERIC_REQUEST_MESSAGE = (
    'If an active account matches that email, a password reset link has been sent.'
)
INVALID_TOKEN_MESSAGE = 'This password reset link is invalid or has expired.'


def _active_user_from_token(uid, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(
            pk=user_id,
            is_active=True,
            status=User.Status.ACTIVE,
        )
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None
    return user if default_token_generator.check_token(user, token) else None


def _record_activity(request, user, activity):
    SystemLog.objects.create(
        user=user,
        activity=activity,
        ip_address=_request_ip(request),
    )


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data['email'].strip(),
            is_active=True,
            status=User.Status.ACTIVE,
        ).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = (
                f"{settings.FRONTEND_URL.rstrip('/')}/reset-password/{uid}/{token}"
            )
            send_mail(
                subject='Reset your TAGAD password',
                message=(
                    f'Hello {user.get_full_name() or user.username},\n\n'
                    'Use the secure link below to reset your TAGAD password:\n'
                    f'{reset_url}\n\n'
                    'If you did not request this, you can ignore this email. '
                    'The link will expire automatically.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            _record_activity(request, user, 'Requested a password reset.')
        return Response({'detail': GENERIC_REQUEST_MESSAGE})


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetValidateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _active_user_from_token(**serializer.validated_data)
        if not user:
            return Response(
                {'detail': INVALID_TOKEN_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'valid': True})


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token_serializer = PasswordResetTokenSerializer(data=request.data)
        token_serializer.is_valid(raise_exception=True)
        user = _active_user_from_token(**token_serializer.validated_data)
        if not user:
            return Response(
                {'detail': INVALID_TOKEN_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PasswordResetConfirmSerializer(
            data=request.data,
            context={'user': user},
        )
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        _record_activity(request, user, 'Completed a password reset.')
        return Response(status=status.HTTP_204_NO_CONTENT)
