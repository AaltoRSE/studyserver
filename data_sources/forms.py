from django import forms
from .models import JsonUrlDataSource, AwareDataSource, GooglePortabilityDataSource, TikTokPortabilityDataSource

class JsonUrlDataSourceForm(forms.ModelForm):
    class Meta:
        model = JsonUrlDataSource
        fields = ['name', 'url']

class AwareDataSourceForm(forms.ModelForm):
    class Meta:
        model = AwareDataSource
        fields = ['name']

class GooglePortabilityDataSourceForm(forms.ModelForm):
    class Meta:
        model = GooglePortabilityDataSource
        fields = ['name']

class TikTokPortabilityDataSourceForm(forms.ModelForm):
    class Meta:
        model = TikTokPortabilityDataSource
        fields = ['name']


class DataFilterForm(forms.Form):
    data_type = forms.ChoiceField(choices=[])
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        data_type_choices = kwargs.pop('data_type_choices', [])
        super().__init__(*args, **kwargs)
        self.fields['data_type'].choices = [(dt, dt.title()) for dt in data_type_choices]

