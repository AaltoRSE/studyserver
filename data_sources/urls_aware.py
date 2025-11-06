from django.urls import path
from . import views_aware

urlpatterns = [
    path('config/<uuid:token>/', views_aware.aware_config_api, name='aware_config_api'),
    path('setup/<uuid:token>/', views_aware.aware_mobile_setup, name='aware_mobile_setup'),
]