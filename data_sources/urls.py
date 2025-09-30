from django.urls import path
from . import views

urlpatterns = [
    path('add/json/', views.add_json_source, name='add_json_source'),
    path('<int:source_id>/', views.view_data_source, name='view_data_source'),
    path('add/aware/', views.add_aware_source, name='add_aware_source'),
    path('instructions/aware/<int:source_id>/', views.aware_instructions, name='aware_instructions'), # Add this
    path('aware_config/<uuid:token>/', views.aware_config_api, name='aware_config_api'),
]