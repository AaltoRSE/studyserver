from django.db import migrations


def convert_source_configs(apps, schema_editor):
    Study = apps.get_model('studies', 'Study')
    for study in Study.objects.all():
        configs = study.source_configurations or {}
        for name in (study.required_data_sources or []):
            if name not in configs:
                configs[name] = {'status': 'required'}
        for name in (study.optional_data_sources or []):
            if name not in configs:
                configs[name] = {'status': 'optional'}
        study.source_configurations = configs
        study.save(update_fields=['source_configurations'])


class Migration(migrations.Migration):

    dependencies = [
        ('studies', '0021_remove_study_domain'),
    ]

    operations = [
        migrations.RunPython(convert_source_configs, migrations.RunPython.noop),
    ]
