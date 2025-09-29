from django import forms
from .models import JsonUrlDataSource

class JsonUrlDataSourceForm(forms.ModelForm):
    class Meta:
        model = JsonUrlDataSource
        fields = ['name', 'url']
