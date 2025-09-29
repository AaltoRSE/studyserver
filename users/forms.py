from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class CustomUserCreationForm(UserCreationForm):
    USER_TYPE_CHOICES = (
        ("researcher", "Researcher"),
        ("participant", "Participant"),
    )
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                user_type=self.cleaned_data.get('user_type')
            )
        return user

