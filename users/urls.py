from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('signup/researcher/', views.signup_researcher, name='signup_researcher'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('token/', views.manage_token, name='manage_token'),
    path('researcher-dashboard/', views.researcher_dashboard, name='researcher_dashboard'),
    path('api/data/', views.my_data_api, name='my_data_api'),
]
