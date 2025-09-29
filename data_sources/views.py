from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import JsonUrlDataSourceForm
from .models import DataSource
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
def view_data_source(request, source_id):
    source = get_object_or_404(DataSource, id=source_id, profile=request.user.profile)
    data = source.get_real_instance().fetch_data()
    pretty_data = json.dumps(data, indent=4)

    context = {
        'source': source,
        'pretty_data': pretty_data,
    }
    return render(request, 'data_sources/view_source.html', context)