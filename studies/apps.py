from django.apps import AppConfig
from django.db.models.signals import post_migrate


def setup_researcher_group(sender, **kwargs):
    from django.contrib.auth.models import Group, Permission
    group, created = Group.objects.get_or_create(name='Researchers')

    required_permissions = [
        'view_study',
        'change_study',
        'view_consent',
    ]

    perms = Permission.objects.filter(codename__in=required_permissions)
    group.permissions.set(perms)


class StudiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'studies'


    def ready(self):
        # Connect the function to the post_migrate signal
        post_migrate.connect(setup_researcher_group, sender=self)