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

    for required_type in study.required_data_sources:
        Consent.objects.get_or_create(
            participant=profile,
            study=study,
            source_type=required_type,
        )

    for optional_type in study.optional_data_sources:
        Consent.objects.get_or_create(
            participant=profile,
            study=study,
            source_type=optional_type,
            is_optional=True
        )
        
    messages.info(request, f"You have started the enrollment process for '{study.title}'. Please complete the required steps.")
    return redirect('dashboard')


def study_detail(request, study_id):
    study = get_object_or_404(Study, pk=study_id)
    html_content = services.get_study_page_html(study.raw_content_base_url)

    template = engines['django'].from_string(html_content)
    
    context = {
        'study': study,
        'request': request,
        'user': request.user,
    }
    return render(request, 'studies/study_detail_wrapper.html', {'study_page_content': template.render(context)})