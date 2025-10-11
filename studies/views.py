from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Study, Consent
from django.contrib import messages


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
