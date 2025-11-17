from django.db import models
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import os
import requests
import secrets
import pandas as pd
from niimpy.reading.google_portability import youtube_history as np_youtube_history

from urllib.parse import urlencode
from .base import DataSource


class GooglePortabilityDataSource(DataSource):
    PROCESSING_STATUS_CHOICES = (
        ('authorized', 'Authorized, waiting for download'),
        ('processing', 'Processing'),
        ('processed', 'Processed successfully'),
        ('error', 'Error during processing'),
    )
    downloaded_files = models.JSONField(default=list, blank=True)
    access_token = models.CharField(max_length=500, blank=True, null=True)
    refresh_token = models.CharField(max_length=500, blank=True, null=True)
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

    # Data processing and handling status 
    CSV_OUTPUT_PATH = 'data/youtube_history_processed.csv'
    job_status = models.JSONField(
        default=dict,
        blank=True,
        help_text="Maps job_id to {'completed': bool, 'downloaded_at': timestamp, 'state': job_state}"
    )
    file_status = models.JSONField(
        default=dict,
        blank=True,
        help_text="Maps filepath to {'processed': bool, 'processed_at': timestamp}"
    )

    def get_setup_url(self):
        return reverse('auth_start', args=[self.id])

    def get_confirm_url(self):
        return reverse('auth_callback', args=[self.id])
    
    def get_instructions_card(self, request):
        # Returns "Authorize with Google" button for dashboard
        return {
            'auth_url': reverse('auth_start', args=[self.id])
        }, 'data_sources/google/instructions_card.html'

    @property
    def display_type(self):
        return "Google Portability Data"

    def get_data_types(self):
        # Placeholder, I know we will at least have YouTube History
        if self.processing_status in ['processed', 'processing']:
            return ['youtube_history'] 
        return []

    def fetch_data(self, data_type, limit=1000, start_date=None, end_date=None):
        if self.processing_status in ['processed', 'processing']:
            return [{"info": f"Data for {data_type} would be fetched here."}]

        if data_type != 'youtube_history':
            return []
        
        try:
            df = pd.read_csv(self.CSV_OUTPUT_PATH)
            df = df[df['device_id'] == str(self.device_id)]

            if start_date:
                df = df[df['timestamp'] >= start_date.timestamp() * 1000]
            if end_date:
                df = df[df['timestamp'] <= end_date.timestamp() * 1000]

            df = df.head(limit)
            return df.to_dict('records')

        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error fetching YouTube data: {e}")
            return []


    def start_processing(self):
        self.save()
        print(f"Triggering background task for GooglePortabilityDataSource ID {self.id}")


    def get_auth_url(self, request):
        state_token = secrets.token_urlsafe(16)
        self.oauth_state = state_token
        self.save()

        redirect_url = request.build_absolute_uri(
            reverse('auth_callback')
        )

        params = {
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'redirect_uri': redirect_url,
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/dataportability.myactivity.youtube',
            'access_type': 'offline',
            'state': state_token,
            'prompt': 'consent',
        }
        auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
        return auth_url
    

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
        headers = {'Authorization': f"Bearer {self.access_token}"}
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

            job_status = self.job_status or {}
            job_status[job_id] = {'completed': False, 'downloaded_at': None, 'state': None}
            self.job_status = job_status
            self.save()

        else:
            return False, "Failed to initiate data export."

        return True, "Authorization successful."
    
    def refresh_access_token(self):
        if not self.refresh_token:
            return False, "No refresh token available."

        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'refresh_token': self.refresh_token,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'grant_type': 'refresh_token',
        }

        try:
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            tokens = response.json()

            self.access_token = tokens['access_token']
            expires_in = tokens.get('expires_in')
            self.token_expiry = timezone.now() + timedelta(seconds=expires_in)
            self.save()
            return True, "Token refreshed successfully."

        except requests.RequestException as e:
            return False, f"Token refresh failed: {e}"
        except KeyError as e:
            return False, f"Error parsing token response: Missing key {e}"
    
    def revoke_before_delete(self):
        # Revoke Google OAuth token
        self.refresh_access_token()
        if self.access_token:
            revoke_url = 'https://dataportability.googleapis.com/v1/authorization:reset'
            headers = {
                'Authorization': f"Bearer {self.access_token}",
                'Content-Type': 'application/json'
            }

            try:
                response = requests.post(revoke_url, headers=headers)
                response.raise_for_status()
                print(f"Successfully revoked Google OAuth token for DataSource ID {self.id}")
            except requests.RequestException as e:
                print(f"Failed to revoke Google OAuth token for DataSource ID {self.id}: {e}")
        
        self.cleanup_files()

    def download_data_files(self):
        # Check if the data export jobs are completed and download files for processing
        self.refresh_access_token()
        if not self.access_token:
            return False, "Cannot download data: No valid access token."
        
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'refresh_token': self.refresh_token,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'grant_type': 'refresh_token',
        }

        try:
            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            tokens = token_response.json()
            access_token = tokens['access_token']
            
            headers = {'Authorization': f"Bearer {access_token}"}
            job_ids = self.data_job_ids
            if not job_ids:
                return False, "No data export jobs found. Please initiate a data export first."
            for job_id in job_ids:
                job_status = self.job_status or {}
                if job_status.get(job_id, {}).get('completed'):
                    continue

                api_url = f'https://dataportability.googleapis.com/v1/archiveJobs/{job_id}/portabilityArchiveState'
                api_response = requests.get(api_url, headers=headers)
                status_data = api_response.json()
                print("Data export status:", status_data)
                if status_data.get('state') != 'COMPLETED':
                    return False, "Data export is still processing. Please check back later."

                download_urls = status_data.get('urls', [])
                for i, url in enumerate(download_urls):
                    file_response = requests.get(url)

                    with open(f'data/google_data_{job_id}_{i}.zip', 'wb') as f:
                        f.write(file_response.content)
                self.downloaded_files.append(f'data/google_data_{job_id}_{i}.zip')
                self.processing_status = 'processing'

                job_status[job_id] = {'completed': True, 'downloaded_at': timezone.now().isoformat(), 'state': 'COMPLETED'}
                self.job_status = job_status
                self.save()

        except requests.RequestException as e:
            return False, f"Error during data retrieval: {e}"
        except KeyError as e:
            return False, f"Error parsing data retrieval response: Missing key {e}"
        except Exception as e:
            return False, f"Unexpected error during data retrieval: {e}"

    def confirm(self, request):
        """User-facing method with messages and redirects."""
        success, message = self.download_data_files()
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('dashboard')
            

    def extract_and_process(self):
        """ Extract the downloaded files and process the data 
        """

        if self.processing_status != 'processing':
            return
        
        try:
            try:
                df = pd.read_csv(self.CSV_OUTPUT_PATH)
            except FileNotFoundError:
                df = pd.DataFrame()
            
            file_status = self.file_status or {}
            for filepath in self.downloaded_files:
                if file_status.get(filepath, {}).get('processed'):
                    continue
                if not os.path.exists(filepath):
                    self.processing_log += f"File not found: {filepath}\n"
                    continue

                read_df = np_youtube_history(filepath)
                read_df["device_id"] = str(self.device_id)
                df = pd.concat([df, read_df], ignore_index=True)

                df.to_csv(self.CSV_OUTPUT_PATH, index=False)
                file_status[filepath] = {'processed': True, 'processed_at': timezone.now().isoformat()}
                self.file_status = file_status

            if not os.path.exists('data'):
                os.makedirs('data')
            self.processing_log += "Data processed successfully.\n"

            all_done = True
            for f in self.downloaded_files:
                if not file_status.get(f, {}).get('processed'):
                    all_done = False
                    break
            if all_done:
                self.processing_status = 'processed'
                self.status = 'active'
                self.save()

        except Exception as e:
            self.processing_log += f"Error during processing: {e}\n"
            self.processing_status = 'error'
            self.save()
            return
            

    def process(self):
        """ Get any available data and process it.
        """
        self.download_data_files()
        self.extract_and_process()
    

    def cleanup_files(self):
        # Delete downloaded files from storage
        for filepath in self.downloaded_files:
            if os.path.exists(filepath):
                os.remove(filepath)
        
        self.processed_files = []
        self.save()
    
