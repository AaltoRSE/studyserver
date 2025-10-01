from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from .forms import JsonUrlDataSourceForm, AwareDataSourceForm
from .models import DataSource, AwareDataSource
import json
import qrcode
import io
import base64

@login_required
def add_json_source(request):
    if request.method == 'POST':
        form = JsonUrlDataSourceForm(request.POST)
        if form.is_valid():
            new_source = form.save(commit=False)
            new_source.profile = request.user.profile
            new_source.save()
            return redirect('dashboard')
    else:
        form = JsonUrlDataSourceForm()
    
    return render(request, 'data_sources/add_source_form.html', {'form': form})

@login_required
def add_aware_source(request):
    if request.method == 'POST':
        form = AwareDataSourceForm(request.POST)
        if form.is_valid():
            # Create the new source, but don't save to the DB yet
            new_source = form.save(commit=False)
            # Assign the current user's profile and save
            new_source.profile = request.user.profile
            new_source.save()
            # Redirect to the instruction page for the newly created source
            return redirect('aware_instructions', source_id=new_source.id)
    else:
        form = AwareDataSourceForm()
    
    return render(request, 'data_sources/add_aware_source.html', {'form': form})


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

    context = {
        'source': source,
        'qr_code_image': qr_b64,
        'qr_link': mobile_setup_url,
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
def view_data_source(request, source_id):
    source = get_object_or_404(DataSource, id=source_id, profile=request.user.profile)
    data = source.get_real_instance().fetch_data()
    pretty_data = json.dumps(data, indent=4)

    context = {
        'source': source,
        'pretty_data': pretty_data,
    }
    return render(request, 'data_sources/view_source.html', context)


@login_required
def confirm_aware_source(request, source_id):
    source = get_object_or_404(AwareDataSource, id=source_id, profile=request.user.profile)
    success, message = source.confirm_device()

    if not success:
        messages.error(request, message)
        return redirect('aware_instructions', source_id=source.id)
    
    messages.success(request, message)
    return redirect('dashboard')


def aware_config_api(request, token):
    config_json = {
        "_id": "",
        "device_label": "test_label",
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
        "sensors": [
            {
                "setting": "location",
                "value": True
            },
        ]
    }
    return JsonResponse(config_json)


