from django.apps import apps

def get_display_type_from_source_type(model_name):
    try:
        ModelClass = apps.get_model('data_sources', model_name)
        return ModelClass.display_type.fget(None)
    except (LookupError, AttributeError):
        return model_name