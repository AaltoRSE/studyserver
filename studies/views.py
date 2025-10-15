from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template import engines
from django.contrib import messages
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.urls import reverse
from urllib.parse import urlencode

from .models import Study, Consent
from .forms import ConsentAcceptanceForm, DataSourceSelectionForm
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
    return redirect('consent_workflow', study_id=study.id)


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


@login_required
def consent_workflow(request, study_id):
    study = get_object_or_404(Study, pk=study_id)
    profile = request.user.profile
    
    consent = Consent.objects.filter(
        participant=profile,
        study=study,
        is_complete=False,
        revocation_date__isnull=True
    ).first()

    if not consent:
        messages.success(request, f"All consents complete for '{study.title}'")
        return redirect('dashboard')

    html_template = services.get_consent_template(study, consent.source_type)
    template = engines['django'].from_string(html_template)
    
    # step 1: show the consent checkbox
    if not consent.consent_text_accepted:
        if request.method == 'POST':
            form = ConsentAcceptanceForm(request.POST)
            if form.is_valid():
                consent.consent_text_accepted = True
                consent.save()
                return redirect('consent_workflow', study_id=study.id)
        else:
            form = ConsentAcceptanceForm()

        checkbox_template = get_template('studies/consent_checkbox_form.html')
        consent_form_html = checkbox_template.render({'form': form}, request)
        
        context = {
            'consent': consent,
            'study': study,
            'consent_form': mark_safe(consent_form_html),
            'request': request,
        }
        rendered = template.render(context)
        return render(request, 'studies/consent_wrapper.html', {
            'content': rendered,
            'scroll_to': 'consent-form'
        })

    # handle the datasource selection box and new datasource button

    available_sources = profile.data_sources.filter(
        polymorphic_ctype__model=consent.source_type.lower(),
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'select':
            form = DataSourceSelectionForm(request.POST, available_sources=available_sources)
            if form.is_valid() and form.cleaned_data['source_id']:
                source = profile.data_sources.filter(id=form.cleaned_data['source_id']).first()
                if source:
                    consent.data_source = source
                    consent.is_complete = True
                    consent.save()
                    return redirect('consent_workflow', study_id=study.id)
        elif action == 'create':
            base_url = reverse('add_data_source', args=[consent.source_type.replace('DataSource', '')])
            query_params = urlencode({'consent_id': consent.id})
            return redirect(f'{base_url}?{query_params}')
    else:
        form = DataSourceSelectionForm(available_sources=available_sources)

    source_form_template = get_template('studies/source_selection_form.html')
    source_form_html = source_form_template.render({'form': form, 'consent': consent}, request)
    
    context = {
        'consent': consent,
        'study': study,
        'consent_form': source_form_html,
    }
    rendered = template.render(context)
    return render(request, 'studies/consent_wrapper.html', {
        'content': rendered,
        'scroll_to': 'consent-form'
    })
