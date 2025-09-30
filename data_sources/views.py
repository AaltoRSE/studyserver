from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from .forms import JsonUrlDataSourceForm, AwareDataSourceForm
from .models import DataSource, AwareDataSource
import uuid
import json


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
    # Allows adding multiple aware sources (multiple devices), but the API serves
    # only one config, which is used for all devices
    if request.method == 'POST':
        form = AwareDataSourceForm(request.POST)
        if form.is_valid():
            new_source = form.save(commit=False)
            new_source.profile = request.user.profile
            new_source.device_id = str(uuid.uuid4())
            new_source.save()
            return redirect('aware_instructions')
        
    else:
        form = AwareDataSourceForm()
    
    return render(request, 'data_sources/add_source_form.html', {'form': form})


@login_required
def aware_instructions(request):
    config_url = request.build_absolute_uri(reverse('aware_config_api'))

    return render(request, 'data_sources/aware_instructions.html', {'config_url': config_url})


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
def aware_config_api(request):
    # TODO: Generate from user-specific configuration (probably stored in data source)
    aware_source = request.user.profile.data_sources.instance_of(AwareDataSource).first()
    device_id = aware_source.device_id if aware_source else "default_device_id"

    config_json = {
        "study_id": "your_study_id",
        "study_url": f"mysql://your_aware_mysql_server/your_aware_db",
        "study_config": [
            {
                "device_id": device_id,
                "sensors": [
                    {"sensor": "accelerometer", "frequency": 20}
                ],
                "plugins": [
                    # ... plugin configs
                ]
            }
        ]
    }
    return JsonResponse(config_json)
