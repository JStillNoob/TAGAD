from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Organization


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
