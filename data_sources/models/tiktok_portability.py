from django.db import models
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import hashlib
import base64
import requests
import secrets
from urllib.parse import urlencode
from .base import DataSource


class TikTokPortabilityDataSource(DataSource):
    PROCESSING_STATUS_CHOICES = (
        ('authorized', 'Authorized, waiting for data'),
        ('data_requested', 'Data portability request submitted'),
        ('processing', 'Processing'),
        ('processed', 'Processed successfully'),
        ('error', 'Error during processing'),
    )
    
    access_token = models.CharField(max_length=500, blank=True, null=True)
    refresh_token = models.CharField(max_length=500, blank=True, null=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    tiktok_user_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    code_verifier = models.CharField(max_length=200, blank=True)

    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='authorized',
    )
    processing_log = models.TextField(blank=True, null=True)

    requires_setup = True
    requires_confirmation = True

    @property
    def display_type(self):
        return "TikTok Portability Data"

    def get_setup_url(self):
        return reverse('auth_start', args=[self.id])
    
    def get_confirm_url(self):
        return reverse('auth_callback', args=[self.id])
    
    def get_data_types(self):
        return ['tiktok_portability']

    def fetch_data(self, data_type, limit=1000, start_date=None, end_date=None):
        if data_type != 'tiktok_portability':
            return []

        if self.processing_status != 'processed':
            return []

        return [{
            'data_type': 'tiktok_portability',
            'data': {'message': 'TikTok portability data fetched successfully.'},
            'fetched_at': timezone.now(),
        }]
    

    @staticmethod
    def generate_pkce_pair():
        """Generate PKCE code_verifier and code_challenge."""
        # Generate random code verifier (43-128 chars)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.replace('=', '')
        
        # Create code challenge: base64-url-encoded SHA256 hash
        code_sha = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_sha).decode('utf-8').replace('=', '')
        
        return code_verifier, code_challenge


    def get_auth_url(self, request):
        code_verifier, code_challenge = self.generate_pkce_pair()
        self.code_verifier = code_verifier
        self.oauth_state = secrets.token_urlsafe(16)
        self.save()

        redirect_url = request.build_absolute_uri(
            reverse('auth_callback')
        )

        params = {
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'response_type': 'code',
            'scope': 'user.info.basic',
            'redirect_uri': redirect_url,
            'state': self.oauth_state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }

        auth_url = f"https://www.tiktok.com/v2/auth/authorize?{urlencode(params)}"
        return auth_url
    
    def handle_auth_callback(self, request):
        code = request.GET.get('code')
        if not code:
            return False, "Authorization code not provided."
        
        if not self.code_verifier:
            return False, "Missing code verifier. Authorization may have expired."

        token_url = 'https://open.tiktokapis.com/v2/oauth/token/'
        token_data = {
            'code': code,
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
            'redirect_uri': request.build_absolute_uri(reverse('auth_callback')),
            'grant_type': 'authorization_code',
            'code_verifier': self.code_verifier,
        }

        try:
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            token_info = response.json()

            self.access_token = token_info['data']['access_token']
            self.refresh_token = token_info['data']['refresh_token']
            expires_in = token_info['data']['expires_in']
            self.token_expiry = timezone.now() + timedelta(seconds=expires_in)
            self.tiktok_user_id = token_info['data']['open_id']
            self.processing_status = 'authorized'
            self.code_verifier = ''
            self.save()
            return True, "Authorization successful."
        
        except requests.RequestException as e:
            return False, f"Error during token exchange: {str(e)}"
        except KeyError:
            return False, "Invalid response from TikTok during token exchange."
        
    def refresh_access_token(self):
        if not self.refresh_token:
            return False, "No refresh token available."

        token_url = 'https://sandbox.tiktok.com/auth/token/'
        token_data = {
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
        }

        try:
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            token_info = response.json()

            self.access_token = token_info['data']['access_token']
            expires_in = token_info['data']['expires_in']
            self.token_expiry = timezone.now() + timedelta(seconds=expires_in)
            self.save()
            return True, "Access token refreshed successfully."
        
        except requests.RequestException as e:
            return False, f"Error during token refresh: {str(e)}"
        except KeyError:
            return False, "Invalid response from TikTok during token refresh."
        
    def _process_data(self):
        if not self.has_active_consent():
            return False, "No consent found."
        pass