from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from .models import AwareDataSource
from studies.models import Consent
import qrcode
import io
import base64
import requests


def _get_aware_instructions_template(request, source, consent_id=None, study_id=None):
    """Helper function to render AWARE instructions HTML."""
    mobile_setup_url = request.build_absolute_uri(
        reverse('aware_mobile_setup', kwargs={'token': source.config_token})
    )
    qr_img = qrcode.make(mobile_setup_url)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    context = {
        'source': source,
        'consent_id': consent_id,
        'qr_code_image': qr_b64,
        'qr_link': mobile_setup_url,
    }
    return context, 'data_sources/aware/instructions_card.html'


@login_required
def aware_instructions(request, source_id):
    source = get_object_or_404(AwareDataSource, id=source_id, profile=request.user.profile)

    consent_id = request.GET.get('consent_id')
    study_id = None
    if consent_id:
        consent = Consent.objects.filter(
            id=consent_id, 
            participant=request.user.profile
        ).first()
        if consent:
            study_id = consent.study.id
        else:
            study_id = None

    context, template = _get_aware_instructions_template(request, source, consent_id, study_id)
    context = {
        'study_id': study_id,
        'instructions_context': context
    }
    return render(request, template, context)


def aware_mobile_setup(request, token):
    source = get_object_or_404(AwareDataSource, config_token=token)
    
    config_url = request.build_absolute_uri(
        reverse('aware_config_api', kwargs={'token': source.config_token})
    )
    
    context = {
        'source': source,
        'config_url': config_url,
        'device_label': source.device_label
    }
    return render(request, 'data_sources/aware/mobile_setup.html', context)


@login_required
def confirm_aware_source(request, source_id):
    source = get_object_or_404(AwareDataSource, id=source_id, profile=request.user.profile)
    success, message = source.confirm_device()

    if not success:
        messages.error(request, message)
        return redirect('dashboard')
    
    messages.success(request, message)
    return redirect('dashboard')


def aware_config_api(request, token):
    source = get_object_or_404(AwareDataSource, config_token=token)
    aware_data_source = source.get_real_instance()

    active_consents = Consent.objects.filter(
        participant=source.profile,
        is_complete=True,
        revocation_date__isnull=True
    )

    studies = [consent.study for consent in active_consents]
    config_json = {
        "_id": "Aalto RSE studypage",
        "device_label": aware_data_source.device_label,
        "study_info": {
            "study_title": "Polalpha",
            "study_description": "Alpha study for POLWELL and POLEMIC",
            "researcher_first": "Jarno",
            "researcher_last": "Rantaharju",
            "researcher_contact": "jarno.rantaharju@aalto.fi"
        },
        "database": {
            "rootPassword": "-",
            "rootUsername": "-",
            "database_host": settings.AWARE_DB_HOST,
            "database_port": settings.AWARE_DB_PORT,
            "database_name": settings.AWARE_DB_NAME,
            "database_password": settings.AWARE_DB_INSERT_PASSWORD,
            "database_username": settings.AWARE_DB_INSERT_USER,
            "require_ssl": True,
            "config_without_password": False
        },
        "createdAt": "",
        "updatedAt": "2025-09-25T12:30:13.411Z",
        "questions": [],
        "schedules": [],
        "sensors": []
    }
    for study in studies:
        config_filename = study.source_configurations.get('AwareDataSource', "aware_config.json")
        base_url = study.raw_content_base_url
        if not base_url:
            continue
        full_config_url = f"{base_url}/{config_filename}"
        try:
            response = requests.get(full_config_url, timeout=5)
            response.raise_for_status()
            study_config = response.json()
            config_json['questions'].extend(study_config.get('questions', []))
            config_json['schedules'].extend(study_config.get('schedules', []))
            config_json['sensors'].extend(study_config.get('sensors', []))
        except requests.exceptions.RequestException:
            print(f"ERROR: Failed to retrieve study config for {study.title}. URL: {full_config_url}")
            continue
            
    return JsonResponse(config_json)