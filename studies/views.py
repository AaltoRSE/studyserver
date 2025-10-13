from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template import engines
from .models import Study, Consent
from django.contrib import messages
from . import services


@login_required
def join_study(request, study_id):
    study = get_object_or_404(Study, pk=study_id)
    profile = request.user.profile

    consent, created = Consent.objects.get_or_create(
        participant=profile,
        study=study
    )
    
    required_sources = study.required_data_sources
    user_sources = [source.model_name for source in profile.data_sources.all()]
    
    missing_sources = [
        source_type for source_type in required_sources if source_type not in user_sources
    ]

    if not missing_sources:
        consent.is_complete = True
        consent.save()
        messages.success(request, f"You have successfully joined '{study.title}'.")
        return redirect('dashboard')
    else:
        next_source_to_add = missing_sources[0].replace('DataSource', '')
        return redirect('add_data_source', source_type=next_source_to_add)

def study_detail(request, study_id):
    study = get_object_or_404(Study, pk=study_id)
    html_content = services.get_study_page_html(study.raw_content_base_url)

    template = engines['django'].from_string(html_content)
    
    context = {
        'study': study,
        'request': request,
    }
    return render(request, 'studies/study_detail_wrapper.html', {'study_page_content': template.render(context)})