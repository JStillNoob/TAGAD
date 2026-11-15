from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0015_camera_ip_scoped_by_organization')]

    operations = [
        migrations.AddField(
            model_name='engagementsummary',
            name='diagnostics',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
