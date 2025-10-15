from django import forms
from django.apps import apps
from .models import Study, DataSource


def get_data_source_type_choices():
    all_models = apps.get_app_config('data_sources').get_models()
    choices = []
    for model in all_models:
        if issubclass(model, DataSource) and model is not DataSource:
            choices.append((model.__name__, model.display_type.fget(None)))
    return choices


class StudyAdminForm(forms.ModelForm):
    required_data_sources = forms.MultipleChoiceField(
        choices=get_data_source_type_choices,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    optional_data_sources = forms.MultipleChoiceField(
        choices=get_data_source_type_choices,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Study
        fields = '__all__'
        exclude = ('source_configurations',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        researchers = cleaned_data.get('researchers')
        
        # This check only applies when a non-superuser is editing an existing study
        if self.instance.pk and not self.user.is_superuser:
            if researchers is None:
                raise forms.ValidationError("Researchers field cannot be empty.")
            if self.user.profile not in researchers:
                raise forms.ValidationError(
                    "You cannot remove yourself from the list of researchers."
                )
            return cleaned_data
        

class ConsentAcceptanceForm(forms.Form):
    accept_consent = forms.BooleanField(required=True, label="I consent")


class DataSourceSelectionForm(forms.Form):
    source_id = forms.ChoiceField(choices=[], required=False, label="Select existing source")
        
    def __init__(self, *args, available_sources=None, **kwargs):
        super().__init__(*args, **kwargs)
        if available_sources:
            self.fields['source_id'].choices = [('', '-- Select a source --')] + [
                (source.id, source.name) for source in available_sources
            ]