from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Camera, Classroom, Organization, Subject, SystemLog


User = get_user_model()


class LoginSerializer(serializers.Serializer):
    identity = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class UserSerializer(serializers.ModelSerializer):
    can_access_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'middle_name',
            'last_name',
            'contact_no',
            'role',
            'status',
            'organization',
            'can_access_admin',
        )
        read_only_fields = fields

    def get_can_access_admin(self, user):
        return bool(
            user.is_active
            and user.is_staff
            and user.status == User.Status.ACTIVE
        )


class RegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    organization_code = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'middle_name',
            'last_name',
            'contact_no',
            'organization_code',
            'password',
            'password_confirmation',
        )
        read_only_fields = ('id',)

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return value

    def validate_organization_code(self, value):
        try:
            return Organization.objects.get(
                organization_code=value.strip(),
                status=Organization.Status.ACTIVE,
            )
        except Organization.DoesNotExist:
            raise serializers.ValidationError('Enter a valid active organization code.')

    def validate(self, attrs):
        password = attrs.get('password')
        if password != attrs.get('password_confirmation'):
            raise serializers.ValidationError({
                'password_confirmation': 'The passwords do not match.',
            })

        candidate = User(
            username=attrs.get('username'),
            email=attrs.get('email'),
            first_name=attrs.get('first_name'),
            middle_name=attrs.get('middle_name', ''),
            last_name=attrs.get('last_name'),
            contact_no=attrs.get('contact_no', ''),
            organization=attrs.get('organization_code'),
        )
        try:
            validate_password(password, user=candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)})

        return attrs

    def create(self, validated_data):
        organization = validated_data.pop('organization_code')
        validated_data.pop('password_confirmation')
        password = validated_data.pop('password')
        return User.objects.create_user(
            **validated_data,
            organization=organization,
            password=password,
            role=User.Role.TEACHER,
            status=User.Status.ACTIVE,
        )


class ManagedUserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.organization_name',
        read_only=True,
        default=None,
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'middle_name',
            'last_name',
            'contact_no',
            'role',
            'status',
            'organization',
            'organization_name',
            'date_joined',
        )
        read_only_fields = fields


class ManagedUserWriteSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.organization_name',
        read_only=True,
        default=None,
    )
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        allow_null=True,
        required=False,
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        required=False,
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'middle_name',
            'last_name',
            'contact_no',
            'role',
            'status',
            'organization',
            'organization_name',
            'date_joined',
            'password',
        )
        read_only_fields = ('id', 'organization_name', 'date_joined')

    def validate_username(self, value):
        value = value.strip()
        users = User.objects.filter(username__iexact=value)
        if self.instance:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        users = User.objects.filter(email__iexact=value)
        if self.instance:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return value

    def validate(self, attrs):
        request_user = self.context['request'].user
        current_role = self.instance.role if self.instance else User.Role.TEACHER
        current_status = self.instance.status if self.instance else User.Status.ACTIVE
        current_organization = self.instance.organization if self.instance else None
        role = attrs.get('role', current_role)
        status_value = attrs.get('status', current_status)
        organization = attrs.get('organization', current_organization)
        errors = {}

        if self.instance == request_user:
            if 'role' in attrs and role != current_role:
                errors['role'] = 'You cannot change your own role.'
            if 'status' in attrs and status_value != current_status:
                errors['status'] = 'You cannot change your own account status.'
            if 'organization' in attrs and organization != current_organization:
                errors['organization'] = 'You cannot change your own organization.'

        if request_user.role == User.Role.ORG_ADMIN:
            if 'role' in attrs and role != User.Role.TEACHER:
                errors['role'] = 'Organization Administrators can only manage Teachers.'
            if 'organization' in attrs and organization != request_user.organization:
                errors['organization'] = 'You can only assign users to your organization.'
            attrs['role'] = User.Role.TEACHER
            attrs['organization'] = request_user.organization
            role = User.Role.TEACHER
            organization = request_user.organization

        if role == User.Role.SYSTEM_ADMIN:
            if organization is not None:
                errors['organization'] = 'System Administrators are not assigned to an organization.'
            attrs['organization'] = None
        elif organization is None:
            errors['organization'] = 'An organization is required for this role.'
        elif organization.status != Organization.Status.ACTIVE:
            errors['organization'] = 'Select an active organization.'

        password = attrs.get('password')
        if self.instance is None and not password:
            errors['password'] = 'A password is required.'
        elif password:
            candidate = self.instance or User()
            for field in ('username', 'email', 'first_name', 'last_name'):
                if field in attrs:
                    setattr(candidate, field, attrs[field])
            try:
                validate_password(password, user=candidate)
            except DjangoValidationError as error:
                errors['password'] = list(error.messages)

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    @staticmethod
    def _sync_access_flags(user):
        user.is_active = user.status == User.Status.ACTIVE
        user.is_staff = user.role == User.Role.SYSTEM_ADMIN
        user.is_superuser = user.role == User.Role.SYSTEM_ADMIN

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        self._sync_access_flags(user)
        user.save(update_fields=['is_active', 'is_staff', 'is_superuser'])
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        self._sync_access_flags(instance)
        instance.save()
        return instance


class ClassroomSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.organization_name',
        read_only=True,
    )
    subject_count = serializers.SerializerMethodField()
    camera_count = serializers.SerializerMethodField()
    capacity = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    class Meta:
        model = Classroom
        fields = (
            'id',
            'organization',
            'organization_name',
            'room_code',
            'building',
            'capacity',
            'subject_count',
            'camera_count',
        )
        read_only_fields = ('id', 'organization_name', 'subject_count', 'camera_count')

    def get_subject_count(self, classroom):
        return classroom.subjects.count()

    def get_camera_count(self, classroom):
        return classroom.cameras.count()

    def validate_room_code(self, value):
        value = value.strip()
        classrooms = Classroom.objects.filter(room_code__iexact=value)
        if self.instance:
            classrooms = classrooms.exclude(pk=self.instance.pk)
        if classrooms.exists():
            raise serializers.ValidationError('A classroom with this room code already exists.')
        return value

    def validate(self, attrs):
        request_user = self.context['request'].user
        organization = attrs.get(
            'organization',
            self.instance.organization if self.instance else None,
        )
        if request_user.role == User.Role.ORG_ADMIN:
            if organization and organization != request_user.organization:
                raise serializers.ValidationError({
                    'organization': 'You can only manage classrooms in your organization.',
                })
            attrs['organization'] = request_user.organization
            organization = request_user.organization
        if organization is None:
            raise serializers.ValidationError({'organization': 'An organization is required.'})
        if organization.status != Organization.Status.ACTIVE:
            raise serializers.ValidationError({'organization': 'Select an active organization.'})
        if (
            self.instance
            and organization != self.instance.organization
            and (self.instance.subjects.exists() or self.instance.cameras.exists())
        ):
            raise serializers.ValidationError({
                'organization': 'A classroom with subjects or cameras cannot be moved to another organization.',
            })
        return attrs


class SubjectSerializer(serializers.ModelSerializer):
    classroom_room_code = serializers.CharField(source='classroom.room_code', read_only=True)
    building = serializers.CharField(source='classroom.building', read_only=True)
    capacity = serializers.IntegerField(source='classroom.capacity', read_only=True)
    organization = serializers.IntegerField(source='classroom.organization_id', read_only=True)
    organization_name = serializers.CharField(
        source='classroom.organization.organization_name',
        read_only=True,
    )
    teacher_name = serializers.SerializerMethodField()
    session_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = (
            'id',
            'subject_code',
            'subject_name',
            'classroom',
            'classroom_room_code',
            'building',
            'capacity',
            'organization',
            'organization_name',
            'teacher',
            'teacher_name',
            'session_count',
        )
        read_only_fields = (
            'id',
            'classroom_room_code',
            'building',
            'capacity',
            'organization',
            'organization_name',
            'teacher_name',
            'session_count',
        )

    def get_teacher_name(self, subject):
        return subject.teacher.get_full_name() or subject.teacher.username

    def get_session_count(self, subject):
        return subject.sessions.count()

    def validate_subject_code(self, value):
        value = value.strip()
        subjects = Subject.objects.filter(subject_code__iexact=value)
        if self.instance:
            subjects = subjects.exclude(pk=self.instance.pk)
        if subjects.exists():
            raise serializers.ValidationError('A subject with this subject code already exists.')
        return value

    def validate(self, attrs):
        request_user = self.context['request'].user
        classroom = attrs.get(
            'classroom',
            self.instance.classroom if self.instance else None,
        )
        teacher = attrs.get(
            'teacher',
            self.instance.teacher if self.instance else None,
        )
        errors = {}

        if classroom is None:
            errors['classroom'] = 'A classroom is required.'
        elif classroom.organization.status != Organization.Status.ACTIVE:
            errors['classroom'] = 'Select a classroom from an active organization.'
        elif (
            request_user.role == User.Role.ORG_ADMIN
            and classroom.organization_id != request_user.organization_id
        ):
            errors['classroom'] = 'You can only manage subjects in your organization.'

        if teacher is None:
            errors['teacher'] = 'A teacher is required.'
        elif teacher.role != User.Role.TEACHER:
            errors['teacher'] = 'The assigned user must have the Teacher role.'
        elif teacher.status != User.Status.ACTIVE or not teacher.is_active:
            errors['teacher'] = 'Select an active teacher.'
        elif classroom and teacher.organization_id != classroom.organization_id:
            errors['teacher'] = 'The teacher must belong to the classroom organization.'

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class CameraSerializer(serializers.ModelSerializer):
    classroom_room_code = serializers.CharField(source='classroom.room_code', read_only=True)
    organization = serializers.IntegerField(source='classroom.organization_id', read_only=True)
    organization_name = serializers.CharField(
        source='classroom.organization.organization_name',
        read_only=True,
    )
    position_label = serializers.CharField(source='get_position_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Camera
        fields = (
            'id',
            'classroom',
            'classroom_room_code',
            'organization',
            'organization_name',
            'camera_name',
            'position',
            'position_label',
            'status',
            'status_label',
        )
        read_only_fields = (
            'id',
            'classroom_room_code',
            'organization',
            'organization_name',
            'position_label',
            'status_label',
        )
        validators = []

    def validate_camera_name(self, value):
        return value.strip()

    def validate(self, attrs):
        request_user = self.context['request'].user
        classroom = attrs.get(
            'classroom',
            self.instance.classroom if self.instance else None,
        )
        camera_name = attrs.get(
            'camera_name',
            self.instance.camera_name if self.instance else '',
        )
        position = attrs.get(
            'position',
            self.instance.position if self.instance else None,
        )
        errors = {}

        if classroom is None:
            errors['classroom'] = 'A classroom is required.'
        elif classroom.organization.status != Organization.Status.ACTIVE:
            errors['classroom'] = 'Select a classroom from an active organization.'
        elif (
            request_user.role == User.Role.ORG_ADMIN
            and classroom.organization_id != request_user.organization_id
        ):
            errors['classroom'] = 'You can only manage cameras in your organization.'

        if classroom:
            matching_names = Camera.objects.filter(
                classroom=classroom,
                camera_name__iexact=camera_name,
            )
            matching_positions = Camera.objects.filter(
                classroom=classroom,
                position=position,
            )
            if self.instance:
                matching_names = matching_names.exclude(pk=self.instance.pk)
                matching_positions = matching_positions.exclude(pk=self.instance.pk)
            if matching_names.exists():
                errors['camera_name'] = 'A camera with this name already exists in the classroom.'
            if matching_positions.exists():
                errors['position'] = 'This camera position is already configured for the classroom.'

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class SystemLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    organization_name = serializers.CharField(
        source='user.organization.organization_name',
        read_only=True,
        default='',
    )

    class Meta:
        model = SystemLog
        fields = (
            'id',
            'user',
            'user_name',
            'username',
            'organization_name',
            'activity',
            'ip_address',
            'logged_at',
        )
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
