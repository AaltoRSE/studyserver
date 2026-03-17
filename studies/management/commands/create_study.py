"""Management command to create the study for this deployment."""
from django.core.management.base import BaseCommand, CommandError
from data_sources.models import DataSource
from studies.models import Study


def get_available_source_types():
    return [cls.__name__ for cls in DataSource.__subclasses__()]


class Command(BaseCommand):
    help = 'Create the study for this deployment. Only one study is allowed per deployment.'

    def handle(self, *args, **options):
        if Study.objects.exists():
            raise CommandError(
                'A study already exists. Only one study per deployment is allowed.'
            )

        source_types = get_available_source_types()

        self.stdout.write('\n=== Create Study ===\n')

        title = input('Study title: ')
        description = input('Description: ')
        contact_name = input('Contact person name: ')
        contact_email = input('Contact person email: ')
        config_url = input('Configuration repository URL: ')
        repo_branch = input('Config repo branch (default: main): ').strip() or 'main'

        self.stdout.write(f'\nAvailable data source types: {", ".join(source_types)}')
        self.stdout.write('Enter comma-separated type names, or leave blank to skip.\n')

        required_input = input('Required data sources: ')
        required_data_sources = [s.strip() for s in required_input.split(',') if s.strip()]
        for name in required_data_sources:
            if name not in source_types:
                raise CommandError(f'Unknown data source type: {name}')

        optional_input = input('Optional data sources: ')
        optional_data_sources = [s.strip() for s in optional_input.split(',') if s.strip()]
        for name in optional_data_sources:
            if name not in source_types:
                raise CommandError(f'Unknown data source type: {name}')

        study = Study.objects.create(
            title=title,
            description=description,
            contact_name=contact_name,
            contact_email=contact_email,
            config_url=config_url,
            repo_branch=repo_branch,
            required_data_sources=required_data_sources,
            optional_data_sources=optional_data_sources,
        )

        self.stdout.write(self.style.SUCCESS(f'\nStudy "{study.title}" created (id={study.id}).'))
