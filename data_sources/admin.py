from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin
from .models import DataSource, JsonUrlDataSource

@admin.register(JsonUrlDataSource)
class JsonUrlDataSourceAdmin(PolymorphicChildModelAdmin):
    base_model = DataSource

@admin.register(DataSource)
class DataSourceAdmin(PolymorphicParentModelAdmin):
    base_model = DataSource
    
    child_models = (JsonUrlDataSource,)