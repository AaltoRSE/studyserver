from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import JsonUrlDataSourceForm

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