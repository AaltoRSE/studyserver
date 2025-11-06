from django.db import models
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import requests
from urllib3 import request
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


    def handle_auth_callback(self, request):
        code = request.GET.get('code')
        if not code:
            messages.error(request, "Google authorization failed: No code returned.")
            return redirect('dashboard')

        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': request.build_absolute_uri(reverse('auth_callback')),
            'grant_type': 'authorization_code',
        }

        try:
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            tokens = response.json()

            self.access_token = tokens['access_token']
            self.refresh_token = tokens.get('refresh_token', '')
            expires_in = tokens.get('expires_in')
            self.token_expiry = timezone.now() + timedelta(seconds=expires_in)
            self.processing_status = 'authorized'
            self.save()

        except requests.RequestException as e:
            return False, f"Token request failed: {e}"
        except KeyError as e:
            return False, f"Error parsing token response: Missing key {e}"

        # Use the token to get the data
        api_url = 'https://dataportability.googleapis.com/v1/portabilityArchive:initiate'
        headers = {'Authorization': f"Bearer {access_token}"}
        body = {'resources': ['myactivity.youtube']}
        api_response = requests.post(api_url, headers=headers, json=body)

        if api_response.ok:
            messages.success(request, "Data export initiated successfully.")
            response_data = api_response.json()
            job_id = response_data.get('archiveJobId')
            # append to the list of job IDs
            job_list = self.data_job_ids or []
            job_list.append(job_id)
            self.data_job_ids = job_list
            self.save()

        else:
            return False, "Failed to initiate data export."

        return True, "Authorization successful."
