from django.contrib.auth import authenticate, login, logout
from django.db.models import Q, Sum
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, serializers, status
from rest_framework.pagination import PageNumberPagination
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
from .permissions import CanAccessClassManagement, CanManageUsers
from .serializers import (
    CameraSerializer,
    ClassroomSerializer,
    LoginSerializer,
    ManagedUserSerializer,
    ManagedUserWriteSerializer,
    RegistrationSerializer,
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
        _log_activity(request, 'Logged in.')
        return Response(UserSerializer(user).data)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _log_activity(request, 'Logged out.')
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _request_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (forwarded_for.split(',')[0].strip() if forwarded_for
            else request.META.get('REMOTE_ADDR', ''))


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


class SystemLogPagination(PageNumberPagination):
    page_size = 20


class SystemLogListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SystemLogSerializer
    pagination_class = SystemLogPagination

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


class ClassroomMixin:
    permission_classes = [CanAccessClassManagement]
    serializer_class = ClassroomSerializer

    def get_queryset(self):
        classrooms = Classroom.objects.select_related('organization').prefetch_related(
            'subjects', 'cameras',
        ).order_by('room_code')
        user = self.request.user
        if user.role == User.Role.ORG_ADMIN:
            classrooms = classrooms.filter(organization=user.organization)
        elif user.role == User.Role.TEACHER:
            classrooms = classrooms.filter(subjects__teacher=user).distinct()
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
        if classroom.subjects.exists() or classroom.cameras.exists():
            raise serializers.ValidationError({
                'detail': 'Remove this classroom’s subjects and cameras before deleting it.',
            })
        description = f'Deleted classroom {classroom.pk} ({classroom.room_code}).'
        classroom.delete()
        _log_activity(request, description)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubjectMixin:
    permission_classes = [CanAccessClassManagement]
    serializer_class = SubjectSerializer

    def get_queryset(self):
        subjects = Subject.objects.select_related(
            'classroom', 'classroom__organization', 'teacher',
        ).prefetch_related('sessions').order_by('subject_code')
        user = self.request.user
        if user.role == User.Role.ORG_ADMIN:
            subjects = subjects.filter(classroom__organization=user.organization)
        elif user.role == User.Role.TEACHER:
            subjects = subjects.filter(teacher=user)
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
        if subject.sessions.exists():
            raise serializers.ValidationError({
                'detail': 'A subject with classroom-session history cannot be deleted.',
            })
        description = f'Deleted subject {subject.pk} ({subject.subject_code}).'
        subject.delete()
        _log_activity(request, description)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClassManagementOptionsView(APIView):
    permission_classes = [CanAccessClassManagement]

    def get(self, request):
        if request.user.role == User.Role.SYSTEM_ADMIN:
            organizations = Organization.objects.filter(
                status=Organization.Status.ACTIVE,
            ).order_by('organization_name')
            teachers = User.objects.filter(
                role=User.Role.TEACHER,
                status=User.Status.ACTIVE,
                is_active=True,
                organization__status=Organization.Status.ACTIVE,
            ).select_related('organization').order_by('first_name', 'last_name', 'username')
        elif request.user.role == User.Role.ORG_ADMIN:
            organizations = Organization.objects.filter(pk=request.user.organization_id)
            teachers = User.objects.filter(
                role=User.Role.TEACHER,
                status=User.Status.ACTIVE,
                is_active=True,
                organization=request.user.organization,
            ).order_by('first_name', 'last_name', 'username')
        else:
            organizations = Organization.objects.none()
            teachers = User.objects.none()

        return Response({
            'organizations': [
                {'id': organization.pk, 'name': organization.organization_name}
                for organization in organizations
            ],
            'teachers': [
                {
                    'id': teacher.pk,
                    'name': teacher.get_full_name() or teacher.username,
                    'organization': teacher.organization_id,
                }
                for teacher in teachers
            ],
            'camera_positions': [
                {'value': value, 'label': label}
                for value, label in Camera.Position.choices
            ],
            'camera_statuses': [
                {'value': value, 'label': label}
                for value, label in Camera.Status.choices
            ],
        })


class CameraMixin:
    permission_classes = [CanAccessClassManagement]
    serializer_class = CameraSerializer

    def get_queryset(self):
        cameras = Camera.objects.select_related(
            'classroom', 'classroom__organization',
        ).order_by('classroom__room_code', 'position')
        user = self.request.user
        if user.role == User.Role.ORG_ADMIN:
            cameras = cameras.filter(classroom__organization=user.organization)
        elif user.role == User.Role.TEACHER:
            cameras = cameras.filter(classroom__subjects__teacher=user).distinct()
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
        if camera.session_cameras.exists():
            raise serializers.ValidationError({
                'detail': 'A camera used by a classroom session cannot be deleted. Deactivate it instead.',
            })
        description = f'Deleted camera {camera.pk} ({camera.camera_name}).'
        camera.delete()
        _log_activity(request, description)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
            classrooms = Classroom.objects.all()
            subjects = Subject.objects.all()
            cameras = Camera.objects.all()
            sessions = ClassroomSession.objects.all()
        elif user.role == User.Role.ORG_ADMIN:
            classrooms = Classroom.objects.filter(organization=user.organization)
            subjects = Subject.objects.filter(classroom__organization=user.organization)
            cameras = Camera.objects.filter(classroom__organization=user.organization)
            sessions = ClassroomSession.objects.filter(
                subject__classroom__organization=user.organization,
            )
        else:
            subjects = Subject.objects.filter(teacher=user)
            classrooms = Classroom.objects.filter(subjects__teacher=user).distinct()
            cameras = Camera.objects.filter(classroom__subjects__teacher=user).distinct()
            sessions = ClassroomSession.objects.filter(user=user)

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
