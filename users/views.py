from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from studies.models import Consent

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

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
    return render(request, 'dashboard.html')
