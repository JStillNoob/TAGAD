from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'

    organization_name = models.CharField(max_length=150)
    organization_code = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255, blank=True)
    contact_email = models.CharField(max_length=100, blank=True)
    contact_no = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organizations'

    def __str__(self):
        return self.organization_name


class User(AbstractUser):
    class Role(models.TextChoices):
        SYSTEM_ADMIN = 'system_admin', 'System Administrator'
        ORG_ADMIN = 'org_admin', 'Organization Administrator'
        TEACHER = 'teacher', 'Teacher'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='users',
        null=True, blank=True,
    )
    middle_name = models.CharField(max_length=50, blank=True)
    contact_no = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TEACHER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = 'users'
        constraints = [
            models.UniqueConstraint(
                Lower('username'),
                name='users_username_ci_unique',
            ),
            models.UniqueConstraint(
                Lower('email'),
                condition=~Q(email=''),
                name='users_email_ci_unique',
            ),
        ]


class Classroom(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='classrooms')
    room_code = models.CharField(max_length=30, unique=True)
    building = models.CharField(max_length=100, blank=True)
    capacity = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'classrooms'

    def __str__(self):
        return self.room_code


class Subject(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='subjects')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    subject_code = models.CharField(max_length=30, unique=True)
    subject_name = models.CharField(max_length=150)

    class Meta:
        db_table = 'subjects'

    def __str__(self):
        return f'{self.subject_code} - {self.subject_name}'


class Camera(models.Model):
    class Position(models.TextChoices):
        FRONT = 'front', 'Front'
        LEFT = 'left', 'Left'
        RIGHT = 'right', 'Right'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='cameras')
    camera_name = models.CharField(max_length=50)
    position = models.CharField(max_length=30, choices=Position.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = 'cameras'
        constraints = [
            models.UniqueConstraint(
                Lower('camera_name'),
                'classroom',
                name='cameras_name_classroom_ci_unique',
            ),
            models.UniqueConstraint(
                fields=('classroom', 'position'),
                name='cameras_classroom_position_unique',
            ),
        ]

    def __str__(self):
        return self.camera_name


class Presentation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='presentations')
    title = models.CharField(max_length=150)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=255)
    total_slides = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'presentations'

    def __str__(self):
        return self.title


class ClassroomSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='sessions')
    presentation = models.ForeignKey(Presentation, on_delete=models.CASCADE, related_name='sessions')
    session_date = models.DateField()
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'classroom_sessions'


class PresentationSlide(models.Model):
    presentation = models.ForeignKey(Presentation, on_delete=models.CASCADE, related_name='slides')
    slide_number = models.IntegerField()
    slide_title = models.CharField(max_length=150, blank=True)
    image_path = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'presentation_slides'

    def __str__(self):
        return f'{self.presentation.title} - Slide {self.slide_number}'


class SessionCamera(models.Model):
    session = models.ForeignKey(ClassroomSession, on_delete=models.CASCADE, related_name='session_cameras')
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='session_cameras')

    class Meta:
        db_table = 'session_cameras'


class SlideEvent(models.Model):
    session = models.ForeignKey(ClassroomSession, on_delete=models.CASCADE, related_name='slide_events')
    slide = models.ForeignKey(PresentationSlide, on_delete=models.CASCADE, related_name='slide_events')
    entered_at = models.DateTimeField()

    class Meta:
        db_table = 'slide_events'


class EngagementSummary(models.Model):
    event = models.ForeignKey(SlideEvent, on_delete=models.CASCADE, related_name='summaries')
    engaged_count = models.IntegerField(default=0)
    attentive_count = models.IntegerField(default=0)
    confused_count = models.IntegerField(default=0)
    bored_count = models.IntegerField(default=0)
    disengaged_count = models.IntegerField(default=0)
    total_detected = models.IntegerField(default=0)
    average_confidence = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'engagement_summaries'


class EngagementAlert(models.Model):
    summary = models.ForeignKey(EngagementSummary, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=50)
    alert_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engagement_alerts'


class Report(models.Model):
    session = models.ForeignKey(ClassroomSession, on_delete=models.CASCADE, related_name='reports')
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=50)
    report_path = models.CharField(max_length=255)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reports'


class SystemLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs')
    activity = models.TextField()
    ip_address = models.CharField(max_length=45, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_logs'
