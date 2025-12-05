from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template import engines
from django.contrib import messages
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.urls import reverse
from urllib.parse import urlencode
from django.http import JsonResponse
from django.utils import timezone
from django.apps import apps

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from study_server.utils import data_to_csv_response
from datetime import datetime
import base64
from data_sources.models import DataSource
from .models import Study, Consent
from .forms import ConsentAcceptanceForm, DataSourceSelectionForm
from . import services


@login_required
def join_study(request, study_id):
    study = get_object_or_404(Study, pk=study_id)
    profile = request.user.profile

    for required_type in study.required_data_sources:
        Consent.objects.create(
            participant=profile,
            study=study,
            source_type=required_type,
        )

    for optional_type in study.optional_data_sources:
        Consent.objects.create(
            participant=profile,
            study=study,
            source_type=optional_type,
            is_optional=True
        )
        
    messages.info(request, f"You have started the enrollment process for '{study.title}'. Please complete the required steps.")
    return redirect('consent_workflow', study_id=study.id)


@login_required
def withdraw_from_study(request, study_id):
    study = get_object_or_404(Study, id=study_id)
    profile = request.user.profile

    if request.method == 'POST':
        consents = Consent.objects.filter(
            participant=profile,
            study=study,
            revocation_date__isnull=True
        )
        for consent in consents:
            consent.data_source = None
            consent.revocation_date = timezone.now()
            consent.is_complete = False
            consent.save()
        
        messages.success(request, f"You have successfully withdrawn from the study '{study.title}'.")
        return redirect('dashboard')
    
    return render(request, 'studies/withdraw.html', {'study': study})


def study_detail(request, study_id):
    study = get_object_or_404(Study, pk=study_id)
    html_content = services.get_study_page_html(study.raw_content_base_url)
    user_in_study = False
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_in_study = Consent.objects.filter(
            participant=request.user.profile,
            study=study,
            revocation_date__isnull=True
        ).exists()

    template = engines['django'].from_string(html_content)
    
    context = {
        'study': study,
        'request': request,
        'user': request.user,
        'user_in_study': user_in_study,
        'config_repository': study.raw_content_base_url,
        'join_or_login_section': "studies/study_page_components/join_or_login_section.html"
    }
    return render(request, 'studies/study_detail_wrapper.html', {'study_page_content': template.render(context)})



def get_next_consent(profile, study, consent_id=None):
    if consent_id:
        return get_object_or_404(
            Consent,
            id=consent_id,
            participant=profile,
            study=study,
            revocation_date__isnull=True
        )
    return Consent.objects.filter(
        participant=profile,
        study=study,
        is_complete=False,
        is_optional=False,
        revocation_date__isnull=True
    ).first()


def consent_checkbox_view(request, consent, study):
    html_template = services.get_consent_template(study, consent.source_type)
    template = engines['django'].from_string(html_template)

    if request.method == 'POST':
        form = ConsentAcceptanceForm(request.POST)
        if form.is_valid():
            consent.consent_text_accepted = True
            if consent.data_source:
                consent.is_complete = True
            consent.save()
            return redirect(f"{reverse('consent_workflow', args=[study.id])}?consent_id={consent.id}")
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


def create_data_source_flow(consent):
    base_url = reverse('add_data_source', args=[consent.source_type.replace('DataSource', '')])
    query_params = urlencode({'consent_id': consent.id})
    return redirect(f'{base_url}?{query_params}')


def select_data_source_view(request, consent, profile, study):
    html_template = services.get_consent_template(study, consent.source_type)
    template = engines['django'].from_string(html_template)

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

@login_required
def consent_workflow(request, study_id):
    study = get_object_or_404(Study, pk=study_id)
    profile = request.user.profile
    consent_id = request.GET.get('consent_id')
    consent = get_next_consent(profile, study, consent_id)

    if not consent:
        messages.success(request, f"All required sources set up for '{study.title}'")
        return redirect('dashboard')
    
    # step 1: show the consent checkbox
    if not consent.consent_text_accepted:
        return consent_checkbox_view(request, consent, study)
    
    # step 2: select or create data source
    available_sources = profile.data_sources.filter(
        polymorphic_ctype__model=consent.source_type.lower(),
    )
    if available_sources.count() == 0:
        return create_data_source_flow(consent)
    else:
        return select_data_source_view(request, consent, profile, study)

def _clean_row(row):
    for k, v in row.items():
        if isinstance(v, bytes):
            try:
                row[k] = v.decode('utf-8')
            except Exception:
                row[k] = base64.b64encode(v).decode('ascii')
    return row

def _parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d") if date_str else None

@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def study_data_api(request, study_id):
    study = get_object_or_404(Study, id=study_id)

    if not request.user.is_superuser:
        if not study.researchers.filter(user=request.user).exists():
            return JsonResponse({'error': 'Unauthorized'}, status=403)

    data_type = request.GET.get('data_type')
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    output_format = request.GET.get('format', 'json')

    start_date = _parse_date(start_date_param)
    end_date = _parse_date(end_date_param)
    
    active_consents = Consent.objects.filter(
        study=study,
        is_complete=True,
        revocation_date__isnull=True,
        data_source__status='active'
    ).select_related('data_source')

    all_data = []
    all_data_types = set()
    for consent in active_consents:
        if not consent.data_source:
            continue
        source = consent.data_source.get_real_instance()
        data_types = source.get_data_types()

        all_data_types.update(data_types)
        if data_type:
            data_types = [data_type] if data_type in data_types else []

        consent_start = _parse_date(consent.consent_date)
        interval_start = max(filter(None, [consent_start, start_date]))
        consent_end = _parse_date(consent.revocation_date) or timezone.now()
        interval_end = min(filter(None, [consent_end, end_date]))

        for dt in data_types:
            data = source.fetch_data(
                data_type=dt,
                start_date=interval_start,
                end_date=interval_end
            )
            for row in data:
                row["data_type"] = dt
                row["source_type"] = consent.source_type
                all_data.append(_clean_row(row))

    if output_format == 'csv':
        return data_to_csv_response(all_data, "study_data.csv")
    else:
        return JsonResponse({
            'study': study.title,
            'data_count': len(all_data),
            'data_types': list(all_data_types),
            'data': all_data
        })
    