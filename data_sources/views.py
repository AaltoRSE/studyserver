from django.apps import apps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from urllib.parse import urlencode
from . import forms
from .forms import JsonUrlDataSourceForm, AwareDataSourceForm, DataFilterForm
from .models import DataSource, AwareDataSource, JsonUrlDataSource
from studies.models import Consent
from datetime import date, datetime, time
import qrcode
import io
import base64
import requests


@login_required
def select_data_source_type(request):
    source_types = []
    all_models = apps.get_app_config('data_sources').get_models()
    for model in all_models:
        if model._meta.proxy:
             continue
        if issubclass(model, DataSource) and model is not DataSource:
            type_name = model.__name__.replace('DataSource', '')
            source_types.append(type_name)
            
    return render(request, 'data_sources/select_source_type.html', {'types': source_types})

def add_data_source(request, source_type):
    consent_id = request.GET.get('consent_id')
    if consent_id:
        query_params = f'?consent_id={consent_id}'
    else:
        query_params = ''

    try:
        # Dynamically get the Model and Form classes
        model_name = f"{source_type}DataSource"
        form_name = f"{source_type}DataSourceForm"
        ModelClass = apps.get_model('data_sources', model_name)
        FormClass = getattr(forms, form_name)

    except (LookupError, AttributeError):
        raise Http404(f"Invalid data source type {source_type}")
    
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            new_source = form.save(commit=False)
            new_source.profile = request.user.profile
            if isinstance(new_source, JsonUrlDataSource):
                new_source.status = 'active'
            new_source.save()

            # Link to consent if coming from consent workflow
            if consent_id:
                consent = Consent.objects.filter(
                    id=consent_id, 
                    participant=request.user.profile
                ).first()
                if consent:
                    consent.data_source = new_source
                    consent.is_complete = True
                    consent.save()
            
            if isinstance(new_source, AwareDataSource):
                base_url = reverse('aware_instructions', args=[new_source.id])
                query_params = urlencode({'consent_id': consent.id})
                return redirect(f'{base_url}?{query_params}')
            else:
                messages.success(request, f"Successfully added data source: {new_source.name}")
                if consent_id:
                    return redirect('consent_workflow', study_id=consent.study.id)
                else:
                    return redirect('dashboard')

    else:
        form = FormClass()
    
    title = f"Add {source_type.replace('_', ' ').title()} Source"
    return render(request, 'data_sources/add_data_source.html', {'form': form, 'title': title})

@require_POST
@login_required
def delete_data_source(request, source_id):
    source = get_object_or_404(DataSource, id=source_id, profile=request.user.profile)
    source_name = source.name
    source.delete()
    messages.success(request, f"Successfully deleted data source: {source_name}")
    return redirect('dashboard')


@login_required
def aware_instructions(request, source_id):
    source = get_object_or_404(AwareDataSource, id=source_id, profile=request.user.profile)

    mobile_setup_url = request.build_absolute_uri(
        reverse('aware_mobile_setup', kwargs={'token': source.config_token})
    )
    qr_img = qrcode.make(mobile_setup_url)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

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

    context = {
        'source': source,
        'qr_code_image': qr_b64,
        'qr_link': mobile_setup_url,
        'study_id': study_id
    }
    return render(request, 'data_sources/aware_instructions.html', context)

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
    return render(request, 'data_sources/aware_mobile_setup.html', context)



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
        config_filename = study.source_configurations.get('AwareDataSource')
        if not config_filename or not study.page_url:
            continue
        base_url = study.page_url.rsplit('/', 1)[0]
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


@login_required
def view_data_source(request, source_id):
    source = get_object_or_404(DataSource, id=source_id, profile=request.user.profile)
    real_instance = source.get_real_instance()

    data_types = real_instance.get_data_types()
    if request.GET:
        form = DataFilterForm(request.GET, data_type_choices=data_types)
    else:
        initial_data = {'start_date': date.today(), 'end_date': date.today()}
        form = DataFilterForm(initial=initial_data, data_type_choices=data_types)

    headers = []
    page_obj = None
    if form.is_valid():
        selected_type = form.cleaned_data.get('data_type')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if selected_type:
            start_datetime = datetime.combine(start_date, time.min) if start_date else None
            end_datetime = datetime.combine(end_date, time.max) if end_date else None
            all_data = real_instance.fetch_data(
                data_type=selected_type, 
                limit=10000,
                start_date=start_datetime,
                end_date=end_datetime
            )

            if all_data:
                headers = all_data[0].keys()
                
                paginator = Paginator(all_data, 100)
                page_number = request.GET.get('page')
                page_obj = paginator.get_page(page_number)

    context = {
        'source': real_instance,
        'form': form,
        'headers': headers,
        'page_obj': page_obj,
    }
    return render(request, 'data_sources/data_source_detail.html', context)


@login_required
def edit_data_source(request, source_id):
    source = get_object_or_404(DataSource, id=source_id, profile=request.user.profile)
    real_instance = source.get_real_instance()

    # Select the correct form based on the model's class
    if isinstance(real_instance, AwareDataSource):
        FormClass = AwareDataSourceForm
    elif isinstance(real_instance, JsonUrlDataSource):
        FormClass = JsonUrlDataSourceForm
    else:
        messages.error(request, "This data source type cannot be edited.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = FormClass(request.POST, instance=real_instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"Successfully updated '{real_instance.name}'.")
            return redirect('dashboard')
    else:
        form = FormClass(instance=real_instance)

    return render(
        request, 
        'data_sources/add_data_source.html', 
        {'form': form, 'title': f'Edit "{real_instance.name}"'}
    )
