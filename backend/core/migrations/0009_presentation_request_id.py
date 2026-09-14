import uuid

from django.db import migrations, models


def populate_request_ids(apps, schema_editor):
    Presentation = apps.get_model('core', 'Presentation')
    for presentation in Presentation.objects.filter(request_id__isnull=True).iterator():
        presentation.request_id = uuid.uuid4()
        presentation.save(update_fields=['request_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_engagement_pipeline_stage1'),
    ]

    operations = [
        migrations.AddField(
            model_name='presentation',
            name='request_id',
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_request_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='presentation',
            name='request_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AddConstraint(
            model_name='presentation',
            constraint=models.UniqueConstraint(
                fields=('user', 'request_id'),
                name='presentation_user_request_unique',
            ),
        ),
        migrations.AlterField(
            model_name='classroomsession',
            name='presentation',
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name='sessions',
                to='core.presentation',
            ),
        ),
    ]
