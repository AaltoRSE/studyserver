from django.urls import path
from . import views

urlpatterns = [
    path('<int:study_id>/', views.study_detail, name='study_detail'),
    path('<int:study_id>/join/', views.join_study, name='join_study'),
    path('<int:study_id>/consent/', views.consent_workflow, name='consent_workflow'),
    #path('<int:study_id>/consent/<int:consent_id>/link/', views.link_data_source, name='link_data_source')
]
