from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('signup/researcher/', views.signup_researcher, name='signup_researcher'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
