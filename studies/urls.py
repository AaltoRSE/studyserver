from django.urls import path
from . import views

urlpatterns = [
    path('<int:study_id>/', views.study_detail, name='study_detail'),
    path('withdraw/<int:study_id>/', views.withdraw_from_study, name='withdraw_from_study'),
    path('<int:study_id>/join/', views.join_study, name='join_study'),
    path('<int:study_id>/consent/', views.consent_workflow, name='consent_workflow'),
    path('revoke/<int:consent_id>/', views.revoke_consent, name='revoke_consent'),
    path('api/<int:study_id>/data/', views.study_data_api, name='study_data_api'),
]
