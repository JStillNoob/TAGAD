from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_remove_subject_organization'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                Lower('username'),
                name='users_username_ci_unique',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                Lower('email'),
                condition=~Q(email=''),
                name='users_email_ci_unique',
            ),
        ),
    ]
