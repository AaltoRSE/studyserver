from celery import shared_task
from .models import DataSource


@shared_task
def process_data_sources():
    """ Run data source processing tasks
    """
    data_sources = DataSource.objects.all()
    for source in data_sources:
        source.process()

    return "Data sources processed."
