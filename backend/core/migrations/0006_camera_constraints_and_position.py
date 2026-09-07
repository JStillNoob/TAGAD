from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_user_identity_ci_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='camera',
            name='position',
            field=models.CharField(
                choices=[('front', 'Front'), ('left', 'Left'), ('right', 'Right')],
                max_length=30,
            ),
        ),
        migrations.AddConstraint(
            model_name='camera',
            constraint=models.UniqueConstraint(
                Lower('camera_name'),
                'classroom',
                name='cameras_name_classroom_ci_unique',
            ),
        ),
        migrations.AddConstraint(
            model_name='camera',
            constraint=models.UniqueConstraint(
                fields=('classroom', 'position'),
                name='cameras_classroom_position_unique',
            ),
        ),
    ]
