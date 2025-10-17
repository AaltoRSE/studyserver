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
    return render(request, 'home.html')

@login_required
def dashboard(request):
    all_consents = Consent.objects.filter(participant=request.user.profile)

    active_consents = all_consents.filter(is_complete=True, revocation_date__isnull=True)
    incomplete_consents = all_consents.filter(is_complete=False, revocation_date__isnull=True)
    past_consents = all_consents.filter(revocation_date__isnull=False)

    context = {
        'active_consents': active_consents,
        'incomplete_consents': incomplete_consents,
        'past_consents': past_consents,
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