from django.urls import path
from . import views_aware

urlpatterns = [
    path('confirm/<int:source_id>/', views_aware.confirm_aware_source, name='confirm_aware_source'),
    path('config/<uuid:token>/', views_aware.aware_config_api, name='aware_config_api'),
    path('setup/<uuid:token>/', views_aware.aware_mobile_setup, name='aware_mobile_setup'),
]