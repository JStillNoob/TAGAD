from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Camera,
    Classroom,
    ClassroomSession,
    EngagementAlert,
    EngagementSummary,
    Organization,
    Subject,
    SystemLog,
    User,
)
from .lifecycle import (
    archive_record,
    filter_lifecycle,
    invalidate_sessions_for_user_ids,
    invalidate_user_sessions,
    restore_record,
)
from .permissions import CanAccessClassManagement, CanManageUsers
from .pagination import StandardResultsSetPagination, paginated_response
from .auth_throttling import (
    clear_login_failures,
    login_throttle_state,
    record_login_failure,
    record_security_throttle,
    throttle_message,
)
from .request_metadata import request_ip
from .serializers import (
    CameraSerializer,
    ClassManagementQuickSetupSerializer,
    ClassroomSerializer,
    LoginSerializer,
    ManagedOrganizationSerializer,
    ManagedUserSerializer,
    ManagedUserWriteSerializer,
    OrganizationSettingsSerializer,
    PasswordSettingsSerializer,
    ProfileSettingsSerializer,
    RegistrationSerializer,
    SettingsOrganizationSerializer,
    SettingsUserSerializer,
    SubjectSerializer,
    SystemLogSerializer,
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
        identity = serializer.validated_data['identity']
        client_ip = request_ip(request)
        throttle = login_throttle_state(identity, client_ip)
        if throttle.limited:
            return Response(
                {
                    'detail': throttle_message('sign-in attempts', throttle.retry_after),
                    'retry_after': throttle.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={'Retry-After': str(throttle.retry_after)},
            )
        user = authenticate(
            request=request,
            username=identity,
            password=serializer.validated_data['password'],
        )
        if user is None:
            throttle = record_login_failure(identity, client_ip)
            if throttle.newly_limited:
                record_security_throttle(
                    request,
                    identity,
                    'Sign-in temporarily restricted after repeated failed attempts.',
                    'login_throttled',
                )
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        clear_login_failures(identity, client_ip)
        login(request, user)
        _log_activity(request, 'Logged in.')
        return Response(UserSerializer(user).data)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class AccountSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = request.user.organization
        return Response({
            'user': SettingsUserSerializer(request.user).data,
            'organization': (
                SettingsOrganizationSerializer(organization).data
                if organization else None
            ),
            'can_edit_organization': bool(
                organization and request.user.role == User.Role.ORG_ADMIN
            ),
        })


class ProfileSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ProfileSettingsSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _log_activity(request, 'Updated own profile.')
        return Response(SettingsUserSerializer(user).data)


class OrganizationSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        if request.user.role != User.Role.ORG_ADMIN or not request.user.organization_id:
            return Response(
                {'detail': 'Only an organization administrator can edit organization settings.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = OrganizationSettingsSerializer(
            request.user.organization,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        organization = serializer.save()
        _log_activity(request, 'Updated organization contact details.')
        return Response(SettingsOrganizationSerializer(organization).data)


class PasswordSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordSettingsSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        update_session_auth_hash(request, user)
        _log_activity(request, 'Changed own password.')
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _log_activity(request, 'Logged out.')
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _request_ip(request):
    return request_ip(request)


def _log_user_change(request, action, user):
    _log_activity(
        request,
        f'{action} user account {user.pk} ({user.username}).',
    )


def _log_activity(request, activity):
    SystemLog.objects.create(
        user=request.user,
        activity=activity,
        ip_address=_request_ip(request),
    )


class SystemLogListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SystemLogSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        logs = SystemLog.objects.select_related(
            'user', 'user__organization',
        ).order_by('-logged_at', '-id')
        user = self.request.user
        if user.role == User.Role.ORG_ADMIN:
            logs = logs.filter(user__organization=user.organization)
        elif user.role == User.Role.TEACHER:
            logs = logs.filter(user=user)

        search = self.request.query_params.get('search', '').strip()
        if search:
            logs = logs.filter(
                Q(user__username__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(activity__icontains=search)
                | Q(ip_address__icontains=search)
            )

        for parameter, lookup in (
            ('date_from', 'logged_at__date__gte'),
            ('date_to', 'logged_at__date__lte'),
        ):
            value = self.request.query_params.get(parameter, '').strip()
            if value:
                parsed = parse_date(value)
                if parsed is None:
                    raise serializers.ValidationError({parameter: 'Use YYYY-MM-DD format.'})
                logs = logs.filter(**{lookup: parsed})

        return logs


class UserManagementMixin:
    permission_classes = [CanManageUsers]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        users = User.objects.select_related('organization').order_by(
            'first_name', 'last_name', 'username',
        )
        if self.request.user.role == User.Role.ORG_ADMIN:
            users = users.filter(
                organization=self.request.user.organization,
                role=User.Role.TEACHER,
            )
        search = self.request.query_params.get('search', '').strip()
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        role = self.request.query_params.get('role', '').strip()
        if role:
            users = users.filter(role=role)
        user_status = self.request.query_params.get('status', '').strip()
        if user_status:
            users = users.filter(status=user_status)
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
        if user.status == User.Status.INACTIVE:
            invalidate_user_sessions(user)
        _log_user_change(self.request, action, user)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            raise serializers.ValidationError({
                'detail': 'You cannot deactivate your own account.',
            })
        if (
            user.role == User.Role.SYSTEM_ADMIN
            and user.status == User.Status.ACTIVE
            and not User.objects.filter(
                role=User.Role.SYSTEM_ADMIN,
                status=User.Status.ACTIVE,
                is_active=True,
            ).exclude(pk=user.pk).exists()
        ):
            raise serializers.ValidationError({
                'detail': 'At least one active System Administrator is required.',
            })
        if user.sessions.filter(ended_at__isnull=True).exists():
            raise serializers.ValidationError({
                'detail': 'End this user’s active classroom session before deactivating the account.',
            })
        if user.status != User.Status.INACTIVE or user.is_active:
            user.status = User.Status.INACTIVE
            user.is_active = False
            user.save(update_fields=['status', 'is_active'])
            invalidate_user_sessions(user)
            _log_user_change(request, 'Deactivated', user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationListView(APIView):
    permission_classes = [CanManageUsers]

    def get(self, request):
        if request.user.role != User.Role.SYSTEM_ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)
        organizations = filter_lifecycle(
            Organization.objects.order_by('organization_name', 'pk'),
            request.query_params.get('lifecycle'),
        )
        if request.query_params.get('lifecycle', 'active') in ('', 'active'):
            organizations = organizations.filter(status=Organization.Status.ACTIVE)
        search = request.query_params.get('search', '').strip()
        if search:
            organizations = organizations.filter(
                Q(organization_name__icontains=search)
                | Q(organization_code__icontains=search)
            )
        return paginated_response(
            request,
            organizations,
            lambda page: ManagedOrganizationSerializer(page, many=True).data,
        )


class OrganizationLifecycleView(APIView):
    permission_classes = [CanManageUsers]

    def _organization(self, request, pk):
        return Organization.objects.filter(pk=pk).first()

    def delete(self, request, pk):
        if request.user.role != User.Role.SYSTEM_ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)
        organization = self._organization(request, pk)
        if organization is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if ClassroomSession.objects.filter(
            subject__classroom__organization=organization,
            ended_at__isnull=True,
        ).exists():
            raise serializers.ValidationError({
                'detail': 'End every active classroom session before archiving this organization.',
            })
        if archive_record(organization, request.user):
            organization.status = Organization.Status.INACTIVE
            organization.save(update_fields=['status'])
            invalidate_sessions_for_user_ids(
                organization.users.values_list('pk', flat=True),
            )
            _log_activity(
                request,
                f'Archived organization {organization.pk} ({organization.organization_code}).',
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, pk):
        if request.user.role != User.Role.SYSTEM_ADMIN:
            return Response(status=status.HTTP_403_FORBIDDEN)
        organization = self._organization(request, pk)
        if organization is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if restore_record(organization):
            organization.status = Organization.Status.ACTIVE
            organization.save(update_fields=['status'])
            _log_activity(
                request,
                f'Restored organization {organization.pk} ({organization.organization_code}).',
            )
        return Response(ManagedOrganizationSerializer(organization).data)


class UserOptionsView(APIView):
    permission_classes = [CanManageUsers]

    def get(self, request):
        roles = (
            User.Role.choices
            if request.user.role == User.Role.SYSTEM_ADMIN
            else [(User.Role.TEACHER, User.Role.TEACHER.label)]
        )

        return Response({
            'roles': [
                {'value': value, 'label': label}
                for value, label in roles
            ],
            'statuses': [
                {'value': value, 'label': label}
                for value, label in User.Status.choices
            ],
        })


def _selected_first(queryset, selected, *ordering):
    if selected.isdigit():
        return queryset.annotate(
            _selected_order=Case(
                When(pk=int(selected), then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        ).order_by('_selected_order', *ordering)
    return queryset.order_by(*ordering)


class ConfigurationLookupView(APIView):
    permission_classes = [CanManageUsers]

    def get(self, request):
        kind = request.query_params.get('kind', '').strip()
        search = request.query_params.get('search', '').strip()
        selected = request.query_params.get('selected', '').strip() if not search else ''
        organization = request.query_params.get('organization', '').strip()

        if kind == 'organizations':
            queryset = Organization.objects.filter(
                status=Organization.Status.ACTIVE,
                archived_at__isnull=True,
            )
            if request.user.role == User.Role.ORG_ADMIN:
                queryset = queryset.filter(pk=request.user.organization_id)
            if search:
                queryset = queryset.filter(
                    Q(organization_name__icontains=search)
                    | Q(organization_code__icontains=search)
                )
            queryset = _selected_first(queryset, selected, 'organization_name', 'pk')
            serialize = lambda page: [
                {
                    'id': item.pk,
                    'label': item.organization_name,
                    'code': item.organization_code,
                }
                for item in page
            ]
        elif kind == 'classrooms':
            queryset = Classroom.objects.filter(
                organization__status=Organization.Status.ACTIVE,
                organization__archived_at__isnull=True,
                archived_at__isnull=True,
            ).select_related('organization').prefetch_related('cameras')
            if request.user.role == User.Role.ORG_ADMIN:
                queryset = queryset.filter(organization=request.user.organization)
            if organization.isdigit():
                queryset = queryset.filter(organization_id=int(organization))
            if search:
                queryset = queryset.filter(
                    Q(room_code__icontains=search)
                    | Q(building__icontains=search)
                    | Q(organization__organization_name__icontains=search)
                )
            queryset = _selected_first(queryset, selected, 'room_code', 'pk')
            serialize = lambda page: [
                {
                    'id': item.pk,
                    'label': f'{item.room_code} — {item.organization.organization_name}',
                    'room_code': item.room_code,
                    'building': item.building,
                    'organization': item.organization_id,
                    'camera_positions': [
                        camera.position
                        for camera in item.cameras.all()
                        if not camera.is_archived
                    ],
                }
                for item in page
            ]
        elif kind == 'teachers':
            queryset = User.objects.filter(
                role=User.Role.TEACHER,
                status=User.Status.ACTIVE,
                is_active=True,
                organization__status=Organization.Status.ACTIVE,
            ).select_related('organization')
            if request.user.role == User.Role.ORG_ADMIN:
                queryset = queryset.filter(organization=request.user.organization)
            if organization.isdigit():
                queryset = queryset.filter(organization_id=int(organization))
            if search:
                queryset = queryset.filter(
                    Q(username__icontains=search)
                    | Q(email__icontains=search)
                    | Q(first_name__icontains=search)
                    | Q(last_name__icontains=search)
                )
            queryset = _selected_first(queryset, selected, 'first_name', 'last_name', 'username')
            serialize = lambda page: [
                {
                    'id': item.pk,
                    'label': item.get_full_name() or item.username,
                    'username': item.username,
                    'organization': item.organization_id,
                }
                for item in page
            ]
        else:
            raise serializers.ValidationError({
                'kind': 'Choose organizations, classrooms, or teachers.',
            })

        return paginated_response(request, queryset, serialize)


class ClassroomMixin:
    permission_classes = [CanAccessClassManagement]
    serializer_class = ClassroomSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        classrooms = Classroom.objects.select_related('organization').prefetch_related(
            'cameras',
        ).annotate(
            _subject_count=Count(
                'subjects',
                filter=Q(subjects__archived_at__isnull=True),
                distinct=True,
            ),
            _camera_count=Count(
                'cameras',
                filter=Q(cameras__archived_at__isnull=True),
                distinct=True,
            ),
        ).order_by('room_code')
        user = self.request.user
        if user.role == User.Role.ORG_ADMIN:
            classrooms = classrooms.filter(organization=user.organization)
        elif user.role == User.Role.TEACHER:
            classrooms = classrooms.filter(subjects__teacher=user).distinct()
        if not self.kwargs.get('pk'):
            lifecycle = self.request.query_params.get('lifecycle', 'active')
            classrooms = filter_lifecycle(
                classrooms,
                lifecycle,
            )
            if lifecycle in ('', 'active'):
                classrooms = classrooms.filter(
                    organization__status=Organization.Status.ACTIVE,
                    organization__archived_at__isnull=True,
                )
        search = self.request.query_params.get('search', '').strip()
        if search:
            classrooms = classrooms.filter(
                Q(room_code__icontains=search)
                | Q(building__icontains=search)
                | Q(organization__organization_name__icontains=search)
            )
        return classrooms


class ClassroomListCreateView(ClassroomMixin, generics.ListCreateAPIView):
    def perform_create(self, serializer):
        classroom = serializer.save()
        _log_activity(
            self.request,
            f'Created classroom {classroom.pk} ({classroom.room_code}).',
        )


class ClassroomDetailView(ClassroomMixin, generics.RetrieveUpdateDestroyAPIView):
    def perform_update(self, serializer):
        classroom = serializer.save()
        _log_activity(
            self.request,
            f'Updated classroom {classroom.pk} ({classroom.room_code}).',
        )

    def destroy(self, request, *args, **kwargs):
        classroom = self.get_object()
        if classroom.subjects.filter(
            sessions__isnull=False,
            sessions__ended_at__isnull=True,
        ).exists():
            raise serializers.ValidationError({
                'detail': 'End every active session in this classroom before archiving it.',
            })
        if archive_record(classroom, request.user):
            _log_activity(
                request,
                f'Archived classroom {classroom.pk} ({classroom.room_code}).',
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClassroomRestoreView(ClassroomMixin, generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        classroom = self.get_object()
        if classroom.organization.is_archived or classroom.organization.status != Organization.Status.ACTIVE:
            raise serializers.ValidationError({
                'detail': 'Restore the classroom organization first.',
            })
        if restore_record(classroom):
            _log_activity(
                request,
                f'Restored classroom {classroom.pk} ({classroom.room_code}).',
            )
        return Response(self.get_serializer(classroom).data)


class SubjectMixin:
    permission_classes = [CanAccessClassManagement]
    serializer_class = SubjectSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        subjects = Subject.objects.select_related(
            'classroom', 'classroom__organization', 'teacher',
        ).annotate(
            _session_count=Count('sessions', distinct=True),
        ).order_by('subject_code', 'pk')
        user = self.request.user
        if user.role == User.Role.ORG_ADMIN:
            subjects = subjects.filter(classroom__organization=user.organization)
        elif user.role == User.Role.TEACHER:
            subjects = subjects.filter(teacher=user)
        if not self.kwargs.get('pk'):
            lifecycle = self.request.query_params.get('lifecycle', 'active')
            subjects = filter_lifecycle(
                subjects,
                lifecycle,
            )
            if lifecycle in ('', 'active'):
                subjects = subjects.filter(
                    classroom__archived_at__isnull=True,
                    classroom__organization__archived_at__isnull=True,
                    classroom__organization__status=Organization.Status.ACTIVE,
                )
        search = self.request.query_params.get('search', '').strip()
        if search:
            subjects = subjects.filter(
                Q(subject_code__icontains=search)
                | Q(subject_name__icontains=search)
                | Q(classroom__room_code__icontains=search)
                | Q(classroom__building__icontains=search)
                | Q(classroom__organization__organization_name__icontains=search)
                | Q(teacher__username__icontains=search)
                | Q(teacher__first_name__icontains=search)
                | Q(teacher__last_name__icontains=search)
            )
        return subjects


class SubjectListCreateView(SubjectMixin, generics.ListCreateAPIView):
    def perform_create(self, serializer):
        subject = serializer.save()
        _log_activity(
            self.request,
            f'Created subject {subject.pk} ({subject.subject_code}).',
        )


class SubjectDetailView(SubjectMixin, generics.RetrieveUpdateDestroyAPIView):
    def perform_update(self, serializer):
        subject = serializer.save()
        _log_activity(
            self.request,
            f'Updated subject {subject.pk} ({subject.subject_code}).',
        )

    def destroy(self, request, *args, **kwargs):
        subject = self.get_object()
        if subject.sessions.filter(ended_at__isnull=True).exists():
            raise serializers.ValidationError({
                'detail': 'End the active classroom session before archiving this subject.',
            })
        if archive_record(subject, request.user):
            _log_activity(
                request,
                f'Archived subject {subject.pk} ({subject.subject_code}).',
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubjectRestoreView(SubjectMixin, generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        subject = self.get_object()
        if (
            subject.classroom.is_archived
            or subject.classroom.organization.is_archived
            or subject.classroom.organization.status != Organization.Status.ACTIVE
        ):
            raise serializers.ValidationError({
                'detail': 'Restore the classroom and its organization first.',
            })
        if subject.teacher.status != User.Status.ACTIVE or not subject.teacher.is_active:
            raise serializers.ValidationError({'detail': 'Reactivate the assigned teacher first.'})
        if restore_record(subject):
            _log_activity(
                request,
                f'Restored subject {subject.pk} ({subject.subject_code}).',
            )
        return Response(self.get_serializer(subject).data)


class ClassManagementOptionsView(APIView):
    permission_classes = [CanAccessClassManagement]

    def get(self, request):
        classrooms = Classroom.objects.filter(
            archived_at__isnull=True,
            organization__archived_at__isnull=True,
            organization__status=Organization.Status.ACTIVE,
        )
        subjects = Subject.objects.filter(
            archived_at__isnull=True,
            classroom__archived_at__isnull=True,
        )
        cameras = Camera.objects.filter(
            archived_at__isnull=True,
            classroom__archived_at__isnull=True,
            classroom__organization__archived_at__isnull=True,
            classroom__organization__status=Organization.Status.ACTIVE,
        )
        if request.user.role == User.Role.ORG_ADMIN:
            classrooms = classrooms.filter(organization=request.user.organization)
            subjects = subjects.filter(classroom__organization=request.user.organization)
            cameras = cameras.filter(classroom__organization=request.user.organization)
        elif request.user.role == User.Role.TEACHER:
            classrooms = classrooms.filter(subjects__teacher=request.user).distinct()
            subjects = subjects.filter(teacher=request.user)
            cameras = cameras.filter(classroom__subjects__teacher=request.user).distinct()

        return Response({
            'camera_positions': [
                {'value': value, 'label': label}
                for value, label in Camera.Position.choices
            ],
            'camera_statuses': [
                {'value': value, 'label': label}
                for value, label in Camera.Status.choices
            ],
            'summary': {
                'classrooms': classrooms.count(),
                'subjects': subjects.count(),
                'cameras': cameras.count(),
                'capacity': classrooms.aggregate(total=Sum('capacity'))['total'] or 0,
            },
        })


class ClassManagementQuickSetupView(APIView):
    permission_classes = [CanAccessClassManagement]

    @staticmethod
    def _nested_save(serializer_class, data, request, field, index=None):
        serializer = serializer_class(data=data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as error:
            detail = error.detail if index is None else {str(index): error.detail}
            raise serializers.ValidationError({field: detail}) from error
        return serializer.save()

    @transaction.atomic
    def post(self, request):
        input_serializer = ClassManagementQuickSetupSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        setup = input_serializer.validated_data

        if 'classroom_id' in setup:
            classrooms = Classroom.objects.filter(
                archived_at__isnull=True,
                organization__archived_at__isnull=True,
                organization__status=Organization.Status.ACTIVE,
            ).select_related('organization')
            if request.user.role == User.Role.ORG_ADMIN:
                classrooms = classrooms.filter(organization=request.user.organization)
            classroom = classrooms.filter(pk=setup['classroom_id']).first()
            if classroom is None:
                raise serializers.ValidationError({
                    'classroom_id': 'Select a classroom you are permitted to manage.',
                })
            created_classroom = False
        else:
            classroom = self._nested_save(
                ClassroomSerializer,
                setup['classroom'],
                request,
                'classroom',
            )
            created_classroom = True

        cameras = []
        for index, camera_data in enumerate(setup['cameras']):
            cameras.append(self._nested_save(
                CameraSerializer,
                {
                    **camera_data,
                    'classroom': classroom.pk,
                    'status': Camera.Status.ACTIVE,
                },
                request,
                'cameras',
                index,
            ))

        subject = None
        if setup.get('subject'):
            subject = self._nested_save(
                SubjectSerializer,
                {**setup['subject'], 'classroom': classroom.pk},
                request,
                'subject',
            )

        _log_activity(
            request,
            f'Completed quick setup for classroom {classroom.pk} '
            f'({classroom.room_code}): {len(cameras)} camera(s) and '
            f'{1 if subject else 0} subject(s).',
        )
        return Response({
            'classroom': ClassroomSerializer(classroom, context={'request': request}).data,
            'cameras': CameraSerializer(cameras, many=True, context={'request': request}).data,
            'subject': (
                SubjectSerializer(subject, context={'request': request}).data
                if subject else None
            ),
            'created_classroom': created_classroom,
        }, status=status.HTTP_201_CREATED)


class CameraMixin:
    permission_classes = [CanAccessClassManagement]
    serializer_class = CameraSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        cameras = Camera.objects.select_related(
            'classroom', 'classroom__organization',
        ).order_by('classroom__room_code', 'position')
        user = self.request.user
        if user.role == User.Role.ORG_ADMIN:
            cameras = cameras.filter(classroom__organization=user.organization)
        elif user.role == User.Role.TEACHER:
            cameras = cameras.filter(classroom__subjects__teacher=user).distinct()
        if not self.kwargs.get('pk'):
            lifecycle = self.request.query_params.get('lifecycle', 'active')
            cameras = filter_lifecycle(
                cameras,
                lifecycle,
            )
            if lifecycle in ('', 'active'):
                cameras = cameras.filter(
                    classroom__archived_at__isnull=True,
                    classroom__organization__archived_at__isnull=True,
                    classroom__organization__status=Organization.Status.ACTIVE,
                )
        return cameras


class CameraListCreateView(CameraMixin, generics.ListCreateAPIView):
    def perform_create(self, serializer):
        camera = serializer.save()
        _log_activity(
            self.request,
            f'Created camera {camera.pk} ({camera.camera_name}).',
        )


class CameraDetailView(CameraMixin, generics.RetrieveUpdateDestroyAPIView):
    def perform_update(self, serializer):
        camera = serializer.save()
        _log_activity(
            self.request,
            f'Updated camera {camera.pk} ({camera.camera_name}).',
        )

    def destroy(self, request, *args, **kwargs):
        camera = self.get_object()
        if camera.session_cameras.filter(session__ended_at__isnull=True).exists():
            raise serializers.ValidationError({
                'detail': 'End the active classroom session before archiving this camera.',
            })
        if archive_record(camera, request.user):
            _log_activity(
                request,
                f'Archived camera {camera.pk} ({camera.camera_name}).',
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CameraRestoreView(CameraMixin, generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        camera = self.get_object()
        if (
            camera.classroom.is_archived
            or camera.classroom.organization.is_archived
            or camera.classroom.organization.status != Organization.Status.ACTIVE
        ):
            raise serializers.ValidationError({
                'detail': 'Restore the classroom and its organization first.',
            })
        if restore_record(camera):
            _log_activity(
                request,
                f'Restored camera {camera.pk} ({camera.camera_name}).',
            )
        return Response(self.get_serializer(camera).data)


def _engagement_snapshot(sessions):
    totals = EngagementSummary.objects.filter(event__session__in=sessions).aggregate(
        engaged=Sum('engaged_count'),
        attentive=Sum('attentive_count'),
        confused=Sum('confused_count'),
        bored=Sum('bored_count'),
        disengaged=Sum('disengaged_count'),
        total_detected=Sum('total_detected'),
    )
    distribution_counts = {
        key: totals[key] or 0
        for key in ('engaged', 'attentive', 'confused', 'bored', 'disengaged')
    }
    total_detected = totals['total_detected'] or 0
    if not total_detected:
        return {
            'has_data': False,
            'total_detected': 0,
            'average_score': None,
            'distribution': {key: 0 for key in distribution_counts},
        }

    return {
        'has_data': True,
        'total_detected': total_detected,
        'average_score': round(
            100 * (distribution_counts['engaged'] + distribution_counts['attentive'])
            / total_detected
        ),
        'distribution': {
            key: round(100 * count / total_detected)
            for key, count in distribution_counts.items()
        },
    }


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == User.Role.SYSTEM_ADMIN:
            classrooms = Classroom.objects.filter(archived_at__isnull=True)
            subjects = Subject.objects.filter(
                archived_at__isnull=True,
                classroom__archived_at__isnull=True,
                classroom__organization__archived_at__isnull=True,
            )
            cameras = Camera.objects.filter(
                archived_at__isnull=True,
                classroom__archived_at__isnull=True,
                classroom__organization__archived_at__isnull=True,
            )
            sessions = ClassroomSession.objects.filter(archived_at__isnull=True)
        elif user.role == User.Role.ORG_ADMIN:
            classrooms = Classroom.objects.filter(
                organization=user.organization,
                archived_at__isnull=True,
            )
            subjects = Subject.objects.filter(
                classroom__organization=user.organization,
                archived_at__isnull=True,
                classroom__archived_at__isnull=True,
            )
            cameras = Camera.objects.filter(
                classroom__organization=user.organization,
                archived_at__isnull=True,
                classroom__archived_at__isnull=True,
            )
            sessions = ClassroomSession.objects.filter(
                subject__classroom__organization=user.organization,
                archived_at__isnull=True,
            )
        else:
            subjects = Subject.objects.filter(teacher=user, archived_at__isnull=True)
            classrooms = Classroom.objects.filter(
                subjects__teacher=user,
                archived_at__isnull=True,
                subjects__archived_at__isnull=True,
            ).distinct()
            cameras = Camera.objects.filter(
                classroom__subjects__teacher=user,
                archived_at__isnull=True,
                classroom__archived_at__isnull=True,
                classroom__subjects__archived_at__isnull=True,
            ).distinct()
            sessions = ClassroomSession.objects.filter(
                user=user,
                archived_at__isnull=True,
            )

        sessions = sessions.filter(started_at__isnull=False)

        today = timezone.localdate()
        today_sessions = sessions.filter(session_date=today)
        recent_sessions = sessions.select_related(
            'subject', 'subject__classroom',
        ).order_by('-started_at')[:5]
        recent_data = []
        for session in recent_sessions:
            engagement = _engagement_snapshot(
                ClassroomSession.objects.filter(pk=session.pk),
            )
            duration = None
            if session.ended_at:
                duration = round((session.ended_at - session.started_at).total_seconds() / 60)
            recent_data.append({
                'id': session.pk,
                'subject_name': session.subject.subject_name,
                'subject_code': session.subject.subject_code,
                'classroom': session.subject.classroom.room_code,
                'date': session.session_date.isoformat(),
                'started_at': session.started_at.isoformat(),
                'duration_minutes': duration,
                'average_engagement': engagement['average_score'],
                'status': 'completed' if session.ended_at else 'ongoing',
            })

        return Response({
            'counts': {
                'classrooms': classrooms.count(),
                'subjects': subjects.count(),
                'cameras': cameras.count(),
                'sessions_today': today_sessions.count(),
            },
            'recent_sessions': recent_data,
            'engagement': _engagement_snapshot(today_sessions),
            'alerts_today': EngagementAlert.objects.filter(
                summary__event__session__in=today_sessions,
                created_at__date=today,
            ).count(),
        })
