from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import Group
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from study_server.utils import data_to_csv_response
from users.models import Profile
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
    all_consents = Consent.objects.filter(participant=request.user.profile)

    # Group all consents by study
    studies_data = {}
    for consent in all_consents.exclude(revocation_date__isnull=False):
        study = consent.study
        if study not in studies_data:
            studies_data[study] = {
                'active_consents': [],
                'incomplete_consents': [],
                'incomplete_with_sources': [],
                'first_instructions_html': None,
            }

        if consent.is_complete:
            studies_data[study]['active_consents'].append(consent)
        else:
            studies_data[study]['incomplete_consents'].append(consent)

            if consent.data_source:
                source = consent.data_source.get_real_instance()
                if source.requires_setup or source.requires_confirmation:
                    studies_data[study]['incomplete_with_sources'].append({
                        'consent': consent,
                        'source': source,
                    })

    for study, data in studies_data.items():
        if data['incomplete_with_sources']:
            first_item = data['incomplete_with_sources'][0]
            data['first_instructions_html'] = first_item['source'].get_instructions_html(
                request,
                consent_id=first_item['consent'].id,
                study_id=study.id
            )
        
        # Add forms for selecting data sources
        for consent in data['incomplete_consents']:
            if not consent.data_source and consent.consent_text_accepted:
                available_sources = request.user.profile.data_sources.filter(
                    polymorphic_ctype__model=consent.source_type.lower(),
                )
                consent.selection_form = DataSourceSelectionForm(
                    available_sources=available_sources
                )

    context = {
        'studies_data': studies_data,
    }
    return render(request, 'dashboard.html', context)


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