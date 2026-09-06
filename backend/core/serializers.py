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
