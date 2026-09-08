import uuid

import django.utils.timezone
from django.db import migrations, models


def populate_ingestion_ids(apps, schema_editor):
    summary_model = apps.get_model('core', 'EngagementSummary')
    for summary in summary_model.objects.filter(ingestion_id__isnull=True).iterator():
        summary.ingestion_id = uuid.uuid4()
        summary.save(update_fields=['ingestion_id'])


class Migration(migrations.Migration):
    dependencies = [('core', '0007_alter_presentationslide_options_and_more')]

    operations = [
        migrations.AddField(
            model_name='slideevent',
            name='disengagement_alert_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='engagementsummary',
            name='captured_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='engagementsummary',
            name='ingestion_id',
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name='engagementsummary',
            name='pipeline_version',
            field=models.CharField(default='legacy', max_length=50),
        ),
        migrations.AddField(
            model_name='engagementsummary',
            name='schema_version',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='engagementsummary',
            name='unclassified_count',
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(populate_ingestion_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='engagementsummary',
            name='ingestion_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
