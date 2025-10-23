from django.urls import path
from . import views_google_portability

urlpatterns = [
    path('oauth/<int:source_id>/', views_google_portability.auth_start, name='google_portability_auth_start'),
    path('oauth/callback/', views_google_portability.auth_callback, name='google_portability_auth_callback'),
    path('oauth/check/<int:source_id>/', views_google_portability.check_and_get, name='google_portability_check_and_get')
]