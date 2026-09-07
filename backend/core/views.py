from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization, SystemLog, User
from .permissions import CanManageUsers
from .serializers import (
    LoginSerializer,
    ManagedUserSerializer,
    ManagedUserWriteSerializer,
    RegistrationSerializer,
    UserSerializer,
)


@method_decorator(csrf_protect, name='dispatch')
class RegistrationView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'detail': 'CSRF cookie set.'})


@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data['identity'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(UserSerializer(user).data)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _request_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (forwarded_for.split(',')[0].strip() if forwarded_for
            else request.META.get('REMOTE_ADDR', ''))


def _log_user_change(request, action, user):
    SystemLog.objects.create(
        user=request.user,
        activity=f'{action} user account {user.pk} ({user.username}).',
        ip_address=_request_ip(request),
    )


class UserManagementMixin:
    permission_classes = [CanManageUsers]

    def get_queryset(self):
        users = User.objects.select_related('organization').order_by(
            'first_name', 'last_name', 'username',
        )
        if self.request.user.role == User.Role.ORG_ADMIN:
            users = users.filter(
                organization=self.request.user.organization,
                role=User.Role.TEACHER,
            )
        return users

    def get_serializer_class(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return ManagedUserSerializer
        return ManagedUserWriteSerializer


class UserListCreateView(UserManagementMixin, generics.ListCreateAPIView):
    def perform_create(self, serializer):
        user = serializer.save()
        _log_user_change(self.request, 'Created', user)


class UserDetailView(UserManagementMixin, generics.RetrieveUpdateDestroyAPIView):
    def perform_update(self, serializer):
        was_inactive = serializer.instance.status == User.Status.INACTIVE
        user = serializer.save()
        action = 'Reactivated' if was_inactive and user.status == User.Status.ACTIVE else 'Updated'
        _log_user_change(self.request, action, user)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            raise serializers.ValidationError({
                'detail': 'You cannot deactivate your own account.',
            })
        if user.status != User.Status.INACTIVE or user.is_active:
            user.status = User.Status.INACTIVE
            user.is_active = False
            user.save(update_fields=['status', 'is_active'])
            _log_user_change(request, 'Deactivated', user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserOptionsView(APIView):
    permission_classes = [CanManageUsers]

    def get(self, request):
        if request.user.role == User.Role.SYSTEM_ADMIN:
            roles = User.Role.choices
            organizations = Organization.objects.filter(
                status=Organization.Status.ACTIVE,
            ).order_by('organization_name')
        else:
            roles = [(User.Role.TEACHER, User.Role.TEACHER.label)]
            organizations = Organization.objects.filter(pk=request.user.organization_id)

        return Response({
            'roles': [
                {'value': value, 'label': label}
                for value, label in roles
            ],
            'statuses': [
                {'value': value, 'label': label}
                for value, label in User.Status.choices
            ],
            'organizations': [
                {'id': organization.pk, 'name': organization.organization_name}
                for organization in organizations
            ],
        })
