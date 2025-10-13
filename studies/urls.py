from django.urls import path
from . import views

urlpatterns = [
    # path('', views.study_list, name='study_list'), # We are skipping this for now
    path('<int:study_id>/', views.study_detail, name='study_detail'),
]