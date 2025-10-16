from django.db import migrations

def add_token_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    try:
        researcher_group = Group.objects.get(name='Researchers')
        token_content_type = ContentType.objects.get(app_label='authtoken', model='token')
        
        token_view_perm = Permission.objects.get(content_type=token_content_type, codename='view_token')
        token_change_perm = Permission.objects.get(content_type=token_content_type, codename='change_token')
        token_delete_perm = Permission.objects.get(content_type=token_content_type, codename='delete_token')

        researcher_group.permissions.add(token_view_perm, token_change_perm, token_delete_perm)
    except (Group.DoesNotExist, ContentType.DoesNotExist, Permission.DoesNotExist):
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('studies', '0008_consent_consent_text_accepted'),
        ('authtoken', '0003_tokenproxy'),
    ]

    operations = [
        migrations.RunPython(add_token_permissions),
    ]