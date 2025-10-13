from django.urls import path
from . import views

urlpatterns = [
    path('<int:study_id>/', views.study_detail, name='study_detail'),
    path('<int:study_id>/join/', views.join_study, name='join_study'),  
]
