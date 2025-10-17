from django.urls import path
from . import views

urlpatterns = [
    path('<int:study_id>/', views.study_detail, name='study_detail'),
    path('<int:study_id>/join/', views.join_study, name='join_study'),
    path('<int:study_id>/consent/', views.consent_workflow, name='consent_workflow'),
    path('api/<int:study_id>/data/', views.study_data_api, name='study_data_api'),
]
