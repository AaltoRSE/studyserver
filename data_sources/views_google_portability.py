from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from urllib.parse import urlencode
import requests
import secrets

from .forms import GooglePortabilityDataSource


@login_required
def auth_start(request, source_id):
    source = get_object_or_404(
        GooglePortabilityDataSource,
        id=source_id,
        profile=request.user.profile
    )
    state = secrets.token_urlsafe(32)
    source.oauth_state = state
    source.save()

    redirect_url = request.build_absolute_uri(
        reverse('google_portability_auth_callback')
    )
    
    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': redirect_url,
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/dataportability.myactivity.youtube',
        'state': state,
        'access_type': 'offline',
        'prompt': 'consent',
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(auth_url)


@login_required
def auth_callback(request):
    error = request.GET.get('error')
    if error:
        messages.error(request, f"Google authorization failed: {error}")
        return redirect('dashboard')

    received_state = request.GET.get('state')
    try:
        source = GooglePortabilityDataSource.objects.get(
            oauth_state=received_state,
            profile=request.user.profile
        )
        source.oauth_state = None
        source.save()
    except GooglePortabilityDataSource.DoesNotExist:
        messages.error(request, "Invalid or expired state parameter.")
        return redirect('dashboard')
    
    code = request.GET.get('code')
    if not code:
        messages.error(request, "Google authorization failed: No code returned.")
        return redirect('dashboard')

    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'redirect_uri': request.build_absolute_uri(reverse('google_portability_auth_callback')),
        'grant_type': 'authorization_code',
    }

    try:
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()
        tokens = response.json()

        source.access_token = tokens['access_token']
        source.refresh_token = tokens.get('refresh_token', '')
        expires_in = tokens.get('expires_in')
        source.token_expiry = timezone.now() + timedelta(seconds=expires_in)
        source.processing_status = 'authorized'
        source.save()

        messages.success(request, "Google account linked successfully. You can now confirm and process your data.")

    except requests.RequestException as e:
        messages.error(request, f"Failed to exchange code for token: {e}")
    except KeyError as e:
         messages.error(request, f"Error parsing token response: Missing key {e}")

    # Use the token to get the data
    api_url = 'https://dataportability.googleapis.com/v1/portabilityArchive:initiate'
    headers = {'Authorization': f"Bearer {source.access_token}"}
    body = {'resources': ['myactivity.youtube']}
    api_response = requests.post(api_url, headers=headers, json=body)

    if api_response.ok:
        messages.success(request, "Data export initiated successfully.")
        response_data = api_response.json()
        job_id = response_data.get('archiveJobId')
        # append to the list of job IDs
        job_list = source.data_job_ids or []
        job_list.append(job_id)
        source.data_job_ids = job_list
        source.save()
        
    else:
        messages.error(request, f"Failed to initiate data export: {api_response.text}")

    return redirect('dashboard')

@login_required
def check_and_get(request, source_id):
    source = get_object_or_404(
        GooglePortabilityDataSource,
        id=source_id,
        profile=request.user.profile
    )
    refresh_token = source.refresh_token
    
    if not refresh_token:
        messages.error(request, "Error fetching data. Please re-authorize the Google account.")
        return redirect('dashboard')

    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'refresh_token': refresh_token,
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
        job_ids = source.data_job_ids
        if not job_ids:
            messages.error(request, "No data export jobs found. Please initiate a data export first.")
            return redirect('dashboard')
        for job_id in job_ids:
            api_url = f'https://dataportability.googleapis.com/v1/archiveJobs/{job_id}/portabilityArchiveState'
            api_response = requests.get(api_url, headers=headers)
            status_data = api_response.json()
            print("Data export status:", status_data)
            if status_data.get('state') != 'COMPLETED':
                messages.info(request, "Data export is still processing. Please check back later.")
                return redirect('dashboard')

        download_urls = status_data.get('urls', [])
        for i, url in enumerate(download_urls):
            file_response = requests.get(url)

            with open(f'data/google_data_{job_id}_{i}.zip', 'wb') as f:
                f.write(file_response.content)
            source.downloaded_files.append(f'data/google_data_{job_id}_{i}.zip')
        source.processing_status = 'processing'
        source.save()
        
    except requests.RequestException as e:
        messages.error(request, f"Error during data retrieval: {e}")
        return redirect('dashboard')
    except KeyError as e:
        messages.error(request, f"Error parsing response: Missing key {e}")
        return redirect('dashboard')
    
    messages.success(request, "Data downloaded successfully and is being processed.")
    return redirect('dashboard')
