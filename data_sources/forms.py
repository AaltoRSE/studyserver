from django import forms
from .models import JsonUrlDataSource, AwareDataSource

class JsonUrlDataSourceForm(forms.ModelForm):
    class Meta:
        model = JsonUrlDataSource
        fields = ['name', 'url']

class AwareDataSourceForm(forms.ModelForm):
    class Meta:
        model = AwareDataSource
        fields = ['name']
