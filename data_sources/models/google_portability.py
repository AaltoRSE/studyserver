from django.db import models
from django.urls import reverse
from .base import DataSource


class GooglePortabilityDataSource(DataSource):
    PROCESSING_STATUS_CHOICES = (
        ('authorized', 'Authorized, waiting for download'),
        ('processing', 'Processing'),
        ('processed', 'Processed successfully'),
        ('error', 'Error during processing'),
    )
    downloaded_files = models.JSONField(default=list, blank=True)
    access_token = models.CharField(max_length=500, blank=True)
    refresh_token = models.CharField(max_length=500, blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    google_user_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    oauth_state = models.CharField(max_length=100, blank=True, null=True)
    processing_status = models.CharField(
        max_length=20, 
        choices=PROCESSING_STATUS_CHOICES, 
        default='uploaded'
    )
    processing_log = models.TextField(blank=True, help_text="Log messages from the processing task.")

    data_job_ids = models.JSONField(default=dict, blank=True)
    requires_setup = True
    requires_confirmation = True

    def get_setup_url(self):
        return reverse('google_portability_auth_start', args=[self.id])

    def get_confirm_url(self):
        return reverse('google_portability_check_and_get', args=[self.id])

    @property
    def display_type(self):
        return "Google Portability Data"

    def get_data_types(self):
        # Placeholder, I know we will at least have YouTube History
        if self.processing_status == 'processed':
            return ['youtube_history'] 
        return []

    def fetch_data(self, data_type, limit=1000, start_date=None, end_date=None):
        if self.processing_status == 'processed':
            return [{"info": f"Data for {data_type} would be fetched here."}]
        return []

    def start_processing(self):
        self.processing_status = 'processing'
        self.save()
        print(f"Triggering background task for GooglePortabilityDataSource ID {self.id}")
