from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from study_server.utils import data_to_csv_response
from users.models import Profile
from studies.models import Study, Consent
from studies.forms import DataSourceSelectionForm
from .forms import CustomUserCreationForm
from studies.models import Consent

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            Profile.objects.create( 
                user=user,
                user_type='participant'
            )
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def signup_researcher(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            user.save()
            
            researcher_group = Group.objects.get(name='Researchers')
            user.groups.add(researcher_group)

            Profile.objects.create(
                user=user,
                user_type='researcher'
            )
            return redirect('login')
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def manage_token(request):
    token, created = Token.objects.get_or_create(user=request.user)
    
    if request.method == 'POST' and 'regenerate' in request.POST:
        token.delete()
        token = Token.objects.create(user=request.user)
        messages.success(request, "Token regenerated successfully!")
        return redirect('manage_token')
    
    context = {
        'token': token,
        'is_researcher': request.user.profile.user_type == 'researcher',
    }
    return render(request, 'users/manage_token.html', context)


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')

@login_required
def dashboard(request):
    if request.user.profile.user_type == 'researcher':
        return redirect('researcher_dashboard')

    all_consents = Consent.objects.filter(participant=request.user.profile)
    context = {}

    studies_data = {}
    for consent in all_consents.exclude(revocation_date__isnull=False):
        study = consent.study
        if study not in studies_data:
            studies_data[study] = {
                'active_consents': [],
                'incomplete_consents': [],
                'incomplete_sources': [],
                'optional_consents': []
            }

        if consent.is_optional:
            if consent.data_source:
                source = consent.data_source.get_real_instance()
            else:
                source = None
            studies_data[study]['optional_consents'].append({
                'consent': consent,
                'source': source,
            })
        elif not consent.is_complete:
            display_type = consent.source_type
            studies_data[study]['incomplete_consents'].append({
                'consent': consent,
                'type_name': display_type,
            })
        else:
            if consent.data_source:
                source = consent.data_source.get_real_instance()
                if source.status == 'pending' and (source.requires_setup or source.requires_confirmation):
                    studies_data[study]['incomplete_sources'].append({
                        'consent': consent,
                        'source': source,
                    })
                else:
                    studies_data[study]['active_consents'].append(consent)

    # Add forms for selecting data sources
    for study, data in studies_data.items():
        for item in data['incomplete_consents']:
            consent = item['consent']
            if not consent.data_source and consent.consent_text_accepted:
                available_sources = request.user.profile.data_sources.filter(
                    polymorphic_ctype__model=consent.source_type.lower(),
                )
                consent.selection_form = DataSourceSelectionForm(
                    available_sources=available_sources
                )
    context['studies_data'] = studies_data
    
    # Find the first incomplete source that requires setup and instructions
    for study, data in studies_data.items():
        if not 'instructions_template' in context:
            for item in data['incomplete_sources']:
                if item['source'].requires_setup:
                    _context, template = item['source'].get_instructions_card(
                        request,
                        consent_id=item['consent'].id,
                        study_id=study.id
                    )
                    context['instructions_template'] = template
                    context['instructions_context'] = _context
                    break
    
    return render(request, 'dashboard.html', context)


@login_required
def researcher_dashboard(request):
    if request.user.profile.user_type != 'researcher':
        messages.error(request, "Access denied: Researcher dashboard is only for researchers.")
        return redirect('dashboard')

    studies = request.user.profile.studies.all()
    studies_data = []

    for study in studies:
        all_consents = Consent.objects.filter(study=study, revocation_date__isnull=True)
        withdrawn = Consent.objects.filter(study=study, revocation_date__isnull=False).count()

        participants = []
        participant_profiles = all_consents.values_list('participant', flat=True).distinct()
        for profile_id in participant_profiles:
            profile = Profile.objects.get(id=profile_id)
            profile = Profile.objects.get(id=profile_id)
            participant_consents = all_consents.filter(participant=profile)
            
            required_consents = participant_consents.filter(is_optional=False)
            optional_consents = participant_consents.filter(is_optional=True)

            required_consents_complete = required_consents.filter(
                is_complete=True,
                data_source__status='active'
            )
            required_complete = required_consents_complete.count()
            required_total = required_consents.count()
            optional_complete = optional_consents.filter(is_complete=True).count()
            optional_total = optional_consents.count()

            status = 'Complete' if required_complete == required_total else 'Incomplete'

            participants.append({
                'id': profile.id,
                'email': profile.user.email,
                'required_complete': required_complete,
                'required_total': required_total,
                'optional_complete': optional_complete,
                'optional_total': optional_total,
                'status': status
            })
            
        studies_data.append({
            'study': study,
            'participants': participants,
            'total_consents': all_consents.count(),
            'withdrawn': withdrawn,
        })

    context = {'studies_data': studies_data}
    return render(request, 'researcher_dashboard.html', context)


@login_required
def participant_detail(request, study_id, participant_id):
    study = get_object_or_404(Study, id=study_id)
    participant = get_object_or_404(Profile, id=participant_id)

    # Verify researcher has access to this study
    if request.user.profile.user_type != 'researcher':
        return redirect('dashboard')
    if not study.researchers.filter(user=request.user).exists() and not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this participant.")
        return redirect('researcher_dashboard')
    
    consents = Consent.objects.filter(study=study, participant=participant)

    consent_info = []
    for consent in consents:
        info = {
            'source_type': consent.source_type,
            'is_optional': consent.is_optional,
            'is_complete': consent.is_complete,
            'consent_text_accepted': consent.consent_text_accepted,
            'consent_date': consent.consent_date,
        }
        if consent.data_source:
            source = consent.data_source.get_real_instance()
            info['data_source'] = {
                'name': source.name,
                'status': source.status,
                'type': source.display_type,
                'date_added': source.date_added,
            }
        else:
            info['data_source'] = None

        consent_info.append(info)

    context = {
        'study': study,
        'participant': participant,
        'consent_info': consent_info,
    }

    return render(request, 'users/participant_detail.html', context)

@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def my_data_api(request):
    data_type = request.GET.get('data_type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    output_format = request.GET.get('format', 'json')

    all_data = []
    all_data_types = set()

    for source in request.user.profile.data_sources.all():
        real_source = source.get_real_instance()
        data_types = real_source.get_data_types()
        if data_type:
            data_types = [data_type] if data_type in data_types else []
        for dt in data_types:
            data = real_source.fetch_data(
                data_type=dt,
                start_date=start_date,
                end_date=end_date
            )
            all_data.extend(data)
            all_data_types.add(dt)
    
    if output_format == 'csv':
        return data_to_csv_response(all_data, "study_data.csv")
    else:
        return JsonResponse({
            'data_count': len(all_data),
            'data_types': list(all_data_types),
            'data': all_data
        })