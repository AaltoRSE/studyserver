from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin
from .models import DataSource, GooglePortabilityDataSource, AwareDataSource, JsonUrlDataSource

COMMON_READ_ONLY_FIELDS = ('device_id',)

@admin.register(JsonUrlDataSource)
class JsonUrlDataSourceAdmin(PolymorphicChildModelAdmin):
    base_model = DataSource
    show_in_index = True
    readonly_fields = COMMON_READ_ONLY_FIELDS

@admin.register(AwareDataSource)
class AwareDataSourceAdmin(PolymorphicChildModelAdmin):
    base_model = DataSource
    show_in_index = True
    readonly_fields = COMMON_READ_ONLY_FIELDS


@admin.register(GooglePortabilityDataSource)
class GooglePortabilityDataSourceAdmin(PolymorphicChildModelAdmin):
    base_model = DataSource
    show_in_index = True
    readonly_fields = COMMON_READ_ONLY_FIELDS + ('data_job_ids', 'access_token', 'refresh_token',)

@admin.register(DataSource)
class DataSourceAdmin(PolymorphicParentModelAdmin):
    base_model = DataSource
    child_models = (JsonUrlDataSource, AwareDataSource, GooglePortabilityDataSource)
